"""Content summarizer - extract key points from saved articles."""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class KeyPoint:
    """A key point extracted from content."""

    text: str
    score: float
    category: str = "general"

    def __lt__(self, other: "KeyPoint") -> bool:
        return self.score < other.score


@dataclass
class SummaryResult:
    """Result of content summarization."""

    original_length: int = 0
    summary: str = ""
    summary_length: int = 0
    compression_ratio: float = 0.0
    method: str = "frequency"
    key_points: list[KeyPoint] = field(default_factory=list)
    key_phrases: list[str] = field(default_factory=list)


@dataclass
class SummaryConfig:
    """Configuration for summarization."""

    max_key_points: int = 5
    min_sentence_length: int = 15
    method: str = "frequency"
    include_phrases: bool = True

    _VALID_METHODS = {"frequency", "hybrid", "first_n", "last_n", "middle"}

    def __post_init__(self) -> None:
        if self.method not in self._VALID_METHODS:
            raise ValueError(
                f"Invalid method '{self.method}'. Must be one of: {self._VALID_METHODS}"
            )


class ContentSummarizer:
    """Extract key points from saved articles using extractive summarization."""

    def __init__(self, config: Optional[SummaryConfig] = None) -> None:
        self.config = config or SummaryConfig()

    def summarize(
        self, text: str, method: Optional[str] = None
    ) -> SummaryResult:
        """Generate a summary with key points from the text.

        Args:
            text: The article text to summarize.
            method: Override the configured summarization method.

        Returns:
            SummaryResult with key points, phrases, and metadata.
        """
        if not text or not text.strip():
            return SummaryResult()

        sentences = self._split_sentences(text)
        if not sentences:
            return SummaryResult(
                original_length=len(text),
                summary=text.strip(),
                summary_length=len(text.strip()),
                compression_ratio=1.0,
                method=method or self.config.method,
            )

        use_method = method or self.config.method
        key_sentences = self._select_sentences(sentences, use_method)
        key_points = self._build_key_points(key_sentences, sentences)
        key_phrases = (
            self._extract_key_phrases(text)
            if self.config.include_phrases
            else []
        )

        summary = " ".join(kp.text for kp in key_points)
        original_length = len(text)
        summary_length = len(summary)
        compression_ratio = (
            summary_length / original_length if original_length > 0 else 0.0
        )

        return SummaryResult(
            original_length=original_length,
            summary=summary,
            summary_length=summary_length,
            compression_ratio=compression_ratio,
            method=use_method,
            key_points=key_points,
            key_phrases=key_phrases,
        )

    def batch_summarize(self, texts: list[str]) -> list[SummaryResult]:
        """Summarize multiple texts.

        Args:
            texts: List of article texts.

        Returns:
            List of SummaryResult objects.
        """
        return [self.summarize(text) for text in texts]

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [
            s.strip()
            for s in sentences
            if len(s.strip()) >= self.config.min_sentence_length
        ]

    def _select_sentences(
        self, sentences: list[str], method: str
    ) -> list[str]:
        """Select key sentences based on method."""
        if not sentences:
            return []

        if method == "frequency":
            return self._frequency_based(sentences)
        elif method == "hybrid":
            return self._hybrid_based(sentences)
        elif method == "first_n":
            return sentences[: self.config.max_key_points]
        elif method == "last_n":
            return sentences[-self.config.max_key_points :]
        elif method == "middle":
            mid = len(sentences) // 2
            half = self.config.max_key_points // 2
            start = max(0, mid - half)
            return sentences[start : start + self.config.max_key_points]
        else:
            return self._frequency_based(sentences)

    def _frequency_based(self, sentences: list[str]) -> list[str]:
        """Select sentences based on word frequency scoring."""
        if not sentences:
            return []

        word_freq: Counter = Counter()
        for sentence in sentences:
            words = self._tokenize(sentence)
            word_freq.update(words)

        sentence_scores: list[tuple[float, int, str]] = []
        for i, sentence in enumerate(sentences):
            words = self._tokenize(sentence)
            if not words:
                sentence_scores.append((0.0, i, sentence))
                continue
            score = sum(word_freq.get(w, 0) for w in words) / len(words)
            sentence_scores.append((score, i, sentence))

        sentence_scores.sort(key=lambda x: (-x[0], x[1]))
        selected = sentence_scores[: self.config.max_key_points]
        selected.sort(key=lambda x: x[1])

        return [s[2] for s in selected]

    def _hybrid_based(self, sentences: list[str]) -> list[str]:
        """Combine frequency scoring with positional bias."""
        if not sentences:
            return []

        freq_sentences = self._frequency_based(sentences)
        freq_set = set(freq_sentences)

        # Add positional bonus: prefer first and last sentences
        scored: list[tuple[float, int, str]] = []
        for i, sentence in enumerate(sentences):
            base_score = 0.0
            if sentence in freq_set:
                base_score = 1.0
            # Positional bonus
            if i == 0:
                base_score += 0.3
            elif i == len(sentences) - 1:
                base_score += 0.2
            # Penalize very short sentences
            words = self._tokenize(sentence)
            if len(words) < 3:
                base_score *= 0.5
            scored.append((base_score, i, sentence))

        scored.sort(key=lambda x: (-x[0], x[1]))
        selected = scored[: self.config.max_key_points]
        selected.sort(key=lambda x: x[1])

        return [s[2] for s in selected]

    def _build_key_points(
        self, sentences: list[str], all_sentences: list[str]
    ) -> list[KeyPoint]:
        """Build KeyPoint objects from selected sentences."""
        if not sentences:
            return []

        word_freq: Counter = Counter()
        for s in all_sentences:
            word_freq.update(self._tokenize(s))

        key_points: list[KeyPoint] = []
        for i, sentence in enumerate(sentences):
            words = self._tokenize(sentence)
            if not words:
                score = 0.0
            else:
                score = sum(word_freq.get(w, 0) for w in words) / len(words)

            # Normalize score to 0-1 range
            max_freq = max(word_freq.values()) if word_freq else 1
            score = min(score / max(max_freq, 1), 1.0)

            category = self._categorize_sentence(i, len(sentences))
            key_points.append(KeyPoint(text=sentence, score=round(score, 4), category=category))

        # Sort by score descending
        key_points.sort(key=lambda kp: kp.score, reverse=True)
        return key_points

    def _categorize_sentence(self, index: int, total: int) -> str:
        """Categorize a sentence based on its position."""
        if total <= 1:
            return "main"
        if index == 0:
            return "main"
        if index == total - 1:
            return "conclusion"
        if index <= total // 3:
            return "main"
        return "supporting"

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words."""
        return re.findall(r"\b[a-z]{2,}\b", text.lower())

    def _extract_key_phrases(self, text: str, max_phrases: int = 10) -> list[str]:
        """Extract key phrases (bigrams and trigrams) from text."""
        words = self._tokenize(text)
        if len(words) < 2:
            return []

        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "under", "again", "further", "then", "once",
            "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
            "neither", "each", "every", "all", "any", "few", "more", "most",
            "other", "some", "such", "no", "only", "own", "same", "than",
            "too", "very", "just", "about", "this", "that", "these", "those",
        }

        # Count bigrams
        bigrams: Counter = Counter()
        for i in range(len(words) - 1):
            bigrams[f"{words[i]} {words[i + 1]}"] += 1

        # Count trigrams
        trigrams: Counter = Counter()
        for i in range(len(words) - 2):
            trigrams[f"{words[i]} {words[i + 1]} {words[i + 2]}"] += 1

        # Combine and rank by frequency
        all_phrases: Counter = Counter()
        all_phrases.update(bigrams)
        all_phrases.update(trigrams)

        # Score phrases: prefer those with content words and higher frequency
        scored_phrases: list[tuple[float, str]] = []
        for phrase, count in all_phrases.items():
            phrase_words = phrase.split()
            content_words = [w for w in phrase_words if w not in stopwords]
            if content_words:
                # Score based on content word ratio and frequency
                content_ratio = len(content_words) / len(phrase_words)
                score = content_ratio * (1 + count)
                scored_phrases.append((score, phrase))

        scored_phrases.sort(key=lambda x: -x[0])
        return [p[1] for p in scored_phrases[:max_phrases]]


class ArticleSummarizer:
    """High-level API for summarizing articles with metadata."""

    def __init__(self, config: Optional[SummaryConfig] = None) -> None:
        self.summarizer = ContentSummarizer(config)

    def summarize_article(
        self,
        title: str,
        content: str,
        author: Optional[str] = None,
        published_date: Optional[str] = None,
    ) -> dict:
        """Summarize an article with full metadata.

        Args:
            title: Article title.
            content: Article body text.
            author: Optional author name.
            published_date: Optional publication date.

        Returns:
            Dict with summary, key points, and metadata.
        """
        result = self.summarizer.summarize(content)
        return {
            "title": title,
            "author": author,
            "published_date": published_date,
            "summary": result.summary,
            "key_points": [
                {"text": kp.text, "score": kp.score, "category": kp.category}
                for kp in result.key_points
            ],
            "key_phrases": result.key_phrases,
            "compression_ratio": result.compression_ratio,
            "original_length": result.original_length,
            "summary_length": result.summary_length,
        }

    def summarize_articles(
        self, articles: list[dict]
    ) -> list[dict]:
        """Summarize multiple articles.

        Args:
            articles: List of article dicts with 'title' and 'content' keys.

        Returns:
            List of summarized article dicts.
        """
        return [
            self.summarize_article(
                title=a.get("title", ""),
                content=a.get("content", ""),
                author=a.get("author"),
                published_date=a.get("published_date"),
            )
            for a in articles
        ]
