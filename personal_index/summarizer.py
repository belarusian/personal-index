"""Content summarization utilities."""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result of content summarization."""

    original_length: int
    summary: str
    summary_length: int
    compression_ratio: float
    method: str
    key_sentences: list[str] = field(default_factory=list)
    key_phrases: list[str] = field(default_factory=list)


class TextSummarizer:
    """Extractive text summarization using various methods."""

    def __init__(self, max_sentences: int = 5, min_sentence_length: int = 10):
        self.max_sentences = max_sentences
        self.min_sentence_length = min_sentence_length

    def summarize(self, text: str, method: str = "frequency") -> SummaryResult:
        """Generate a summary of the text."""
        if not text or not text.strip():
            return SummaryResult(
                original_length=0,
                summary="",
                summary_length=0,
                compression_ratio=0.0,
                method=method,
            )

        sentences = self._split_sentences(text)
        if not sentences:
            return SummaryResult(
                original_length=len(text),
                summary=text,
                summary_length=len(text),
                compression_ratio=1.0,
                method=method,
            )

        if method == "frequency":
            key_sentences = self._frequency_based(sentences)
        elif method == "first_n":
            key_sentences = self._first_n(sentences)
        elif method == "last_n":
            key_sentences = self._last_n(sentences)
        elif method == "middle":
            key_sentences = self._middle(sentences)
        else:
            raise ValueError(f"Unknown method: {method}")

        summary = " ".join(key_sentences)
        original_length = len(text)
        summary_length = len(summary)
        compression_ratio = summary_length / original_length if original_length > 0 else 0.0

        key_phrases = self._extract_key_phrases(text)

        return SummaryResult(
            original_length=original_length,
            summary=summary,
            summary_length=summary_length,
            compression_ratio=compression_ratio,
            method=method,
            key_sentences=key_sentences,
            key_phrases=key_phrases,
        )

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Split on sentence-ending punctuation followed by space or end
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Filter out empty and too-short sentences
        return [s.strip() for s in sentences if len(s.strip()) >= self.min_sentence_length]

    def _frequency_based(self, sentences: list[str]) -> list[str]:
        """Select sentences based on word frequency."""
        if not sentences:
            return []

        # Count word frequencies across all sentences
        word_freq: Counter = Counter()
        for sentence in sentences:
            words = self._tokenize(sentence)
            word_freq.update(words)

        # Score each sentence by sum of word frequencies
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            words = self._tokenize(sentence)
            if not words:
                sentence_scores.append((0, i, sentence))
                continue
            score = sum(word_freq.get(w, 0) for w in words) / len(words)
            sentence_scores.append((score, i, sentence))

        # Sort by score descending, then by original order
        sentence_scores.sort(key=lambda x: (-x[0], x[1]))

        # Take top N sentences, then sort back by original order
        selected = sentence_scores[:self.max_sentences]
        selected.sort(key=lambda x: x[1])

        return [s[2] for s in selected]

    def _first_n(self, sentences: list[str]) -> list[str]:
        """Take the first N sentences."""
        return sentences[:self.max_sentences]

    def _last_n(self, sentences: list[str]) -> list[str]:
        """Take the last N sentences."""
        return sentences[-self.max_sentences:]

    def _middle(self, sentences: list[str]) -> list[str]:
        """Take sentences from the middle of the text."""
        mid = len(sentences) // 2
        half = self.max_sentences // 2
        start = max(0, mid - half)
        end = start + self.max_sentences
        return sentences[start:end]

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words."""
        return re.findall(r'\b[a-z]{2,}\b', text.lower())

    def _extract_key_phrases(self, text: str, max_phrases: int = 10) -> list[str]:
        """Extract key phrases from text."""
        # Simple approach: find bigrams and trigrams with high frequency
        words = self._tokenize(text)
        if len(words) < 2:
            return []

        ngrams: Counter = Counter()
        for i in range(len(words) - 1):
            ngrams[f"{words[i]} {words[i+1]}"] += 1
        if len(words) >= 3:
            for i in range(len(words) - 2):
                ngrams[f"{words[i]} {words[i+1]} {words[i+2]}"] += 1

        return [phrase for phrase, _ in ngrams.most_common(max_phrases)]

    def truncate(self, text: str, max_length: int = 200, suffix: str = "...") -> str:
        """Truncate text to a maximum length."""
        if len(text) <= max_length:
            return text
        truncated = text[:max_length].rsplit(" ", 1)[0]
        return truncated + suffix
