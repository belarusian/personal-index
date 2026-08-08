"""Content summarization for indexed pages."""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SummaryResult:
    """Result of a summarization operation."""
    original_length: int = 0
    summary_length: int = 0
    compression_ratio: float = 0.0
    summary_text: str = ""
    key_sentences: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_length": self.original_length,
            "summary_length": self.summary_length,
            "compression_ratio": round(self.compression_ratio, 2),
            "summary_text": self.summary_text,
            "key_sentences": self.key_sentences,
            "key_phrases": self.key_phrases,
            "topics": self.topics,
        }


class Summarizer:
    """Summarize content using extractive methods."""

    def __init__(self, max_sentences: int = 5, min_sentence_length: int = 20):
        self.max_sentences = max_sentences
        self.min_sentence_length = min_sentence_length

    def summarize(self, text: str) -> SummaryResult:
        """Generate an extractive summary of the text."""
        if not text or not text.strip():
            return SummaryResult()

        original_length = len(text)
        sentences = self._split_sentences(text)

        if not sentences:
            return SummaryResult(
                original_length=original_length,
                summary_text=text[:500],
            )

        scored = self._score_sentences(sentences)
        top_sentences = sorted(scored, key=lambda x: x[1], reverse=True)[:self.max_sentences]

        # Reorder by original position
        top_sentences.sort(key=lambda x: x[2])
        summary_sentences = [s[0] for s in top_sentences]

        summary_text = " ".join(summary_sentences)
        key_phrases = self._extract_key_phrases(text)

        return SummaryResult(
            original_length=original_length,
            summary_length=len(summary_text),
            compression_ratio=1.0 - (len(summary_text) / original_length) if original_length > 0 else 0.0,
            summary_text=summary_text,
            key_sentences=summary_sentences,
            key_phrases=key_phrases,
        )

    def summarize_paragraphs(self, text: str, max_paragraphs: int = 3) -> SummaryResult:
        """Summarize by selecting the most important paragraphs."""
        if not text or not text.strip():
            return SummaryResult()

        original_length = len(text)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        if len(paragraphs) <= max_paragraphs:
            return SummaryResult(
                original_length=original_length,
                summary_text=text,
                key_sentences=paragraphs,
            )

        scored = []
        for i, para in enumerate(paragraphs):
            score = self._score_paragraph(para)
            scored.append((para, score, i))

        top = sorted(scored, key=lambda x: x[1], reverse=True)[:max_paragraphs]
        top.sort(key=lambda x: x[2])

        summary_text = "\n\n".join(p[0] for p in top)

        return SummaryResult(
            original_length=original_length,
            summary_length=len(summary_text),
            compression_ratio=1.0 - (len(summary_text) / original_length) if original_length > 0 else 0.0,
            summary_text=summary_text,
            key_sentences=[p[0] for p in top],
        )

    def extract_headlines(self, text: str, max_count: int = 5) -> List[str]:
        """Extract headline-like sentences (short, impactful)."""
        sentences = self._split_sentences(text)
        headlines = []
        for s in sentences:
            words = s.split()
            if 3 <= len(words) <= 15 and len(s) < 200:
                headlines.append(s.strip())
        return headlines[:max_count]

    def get_brief(self, text: str, max_words: int = 50) -> str:
        """Get a very brief summary (first N words of key content)."""
        if not text:
            return ""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Handle common sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) >= self.min_sentence_length]

    def _score_sentences(self, sentences: List[str]) -> List[Tuple[str, float, int]]:
        """Score sentences for importance. Returns (sentence, score, position)."""
        scored = []
        word_freq = self._compute_word_frequency(sentences)
        total_sentences = len(sentences)

        for i, sentence in enumerate(sentences):
            score = 0.0
            words = self._tokenize(sentence)
            word_count = len(words)

            if word_count == 0:
                scored.append((sentence, 0.0, i))
                continue

            # Frequency score
            freq_score = sum(word_freq.get(w, 0) for w in words) / word_count

            # Position bonus (first and last sentences are often important)
            position_score = 0.0
            if i == 0:
                position_score = 2.0
            elif i == total_sentences - 1:
                position_score = 1.0
            elif i < 3:
                position_score = 0.5

            # Length bonus (not too short, not too long)
            length_score = 0.0
            if 10 <= word_count <= 30:
                length_score = 1.0
            elif word_count < 10:
                length_score = 0.5
            elif word_count > 50:
                length_score = 0.3

            # Keyword density bonus
            keyword_words = {w for w in words if w.isalpha() and len(w) > 3}
            keyword_density = len(keyword_words) / word_count if word_count > 0 else 0
            keyword_score = keyword_density * 2.0

            score = (freq_score * 0.3 + position_score * 0.25 +
                     length_score * 0.2 + keyword_score * 0.25)

            scored.append((sentence, score, i))

        return scored

    def _score_paragraph(self, paragraph: str) -> float:
        """Score a paragraph for importance."""
        words = self._tokenize(paragraph)
        if not words:
            return 0.0

        # Length score
        length = len(words)
        length_score = min(1.0, length / 100.0)

        # Keyword density
        keyword_words = {w for w in words if w.isalpha() and len(w) > 3}
        keyword_density = len(keyword_words) / length

        # Sentence count
        sentences = self._split_sentences(paragraph)
        sentence_score = min(1.0, len(sentences) / 5.0)

        return length_score * 0.3 + keyword_density * 0.4 + sentence_score * 0.3

    def _compute_word_frequency(self, sentences: List[str]) -> Dict[str, int]:
        """Compute word frequency across all sentences."""
        freq: Dict[str, int] = {}
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "because",
            "but", "and", "or", "if", "while", "that", "this", "these",
            "those", "it", "its", "i", "me", "my", "we", "our", "you",
            "your", "he", "him", "his", "she", "her", "they", "them",
            "what", "which", "who", "whom", "about", "up", "down",
        }

        for sentence in sentences:
            words = self._tokenize(sentence)
            for word in words:
                if word.lower() not in stop_words and len(word) > 2:
                    freq[word.lower()] = freq.get(word.lower(), 0) + 1

        return freq

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        return re.findall(r'\b[a-zA-Z]+\b', text.lower())

    def _extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases from text."""
        sentences = self._split_sentences(text)
        word_freq = self._compute_word_frequency(sentences)

        # Find bigrams with high combined frequency
        bigram_freq: Dict[str, float] = {}
        for sentence in sentences:
            words = self._tokenize(sentence)
            for i in range(len(words) - 1):
                if words[i].isalpha() and words[i+1].isalpha():
                    bigram = f"{words[i]} {words[i+1]}"
                    freq_i = word_freq.get(words[i], 0)
                    freq_j = word_freq.get(words[i+1], 0)
                    bigram_freq[bigram] = bigram_freq.get(bigram, 0) + (freq_i + freq_j)

        sorted_bigrams = sorted(bigram_freq.items(), key=lambda x: x[1], reverse=True)
        return [b[0] for b in sorted_bigrams[:max_phrases]]
