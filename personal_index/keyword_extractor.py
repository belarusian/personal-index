"""Keyword extraction from text using frequency analysis."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple

from personal_index.text_utils import tokenize


@dataclass
class Keyword:
    """A keyword with its frequency and score."""
    text: str
    frequency: int
    score: float
    positions: List[int] = None  # positions in text

    def __post_init__(self):
        if self.positions is None:
            self.positions = []


class KeywordExtractor:
    """Extract keywords from text using frequency-based analysis."""

    def __init__(
        self,
        min_length: int = 3,
        max_keywords: int = 20,
        min_frequency: int = 1,
    ):
        self.min_length = min_length
        self.max_keywords = max_keywords
        self.min_frequency = min_frequency

    def extract(self, text: str) -> List[Keyword]:
        """Extract keywords from text."""
        if not text:
            return []
        tokens = tokenize(text, remove_stopwords=True)
        tokens = [t for t in tokens if len(t) >= self.min_length]
        if not tokens:
            return []

        freq = Counter(tokens)
        freq = {k: v for k, v in freq.items() if v >= self.min_frequency}

        # Calculate positions for each keyword
        positions: Dict[str, List[int]] = {}
        for i, token in enumerate(tokens):
            if token in freq:
                if token not in positions:
                    positions[token] = []
                positions[token].append(i)

        # Score keywords: frequency * log(1 + frequency) for emphasis on repeats
        keywords = []
        for word, count in freq.items():
            score = count * math.log(1 + count)
            keywords.append(Keyword(
                text=word,
                frequency=count,
                score=score,
                positions=positions.get(word, []),
            ))

        # Sort by score descending
        keywords.sort(key=lambda k: k.score, reverse=True)
        return keywords[: self.max_keywords]

    def extract_phrases(self, text: str, n: int = 2) -> List[Tuple[str, int]]:
        """Extract n-gram phrases from text."""
        if not text:
            return []
        tokens = tokenize(text, remove_stopwords=True)
        tokens = [t for t in tokens if len(t) >= self.min_length]
        if len(tokens) < n:
            return []

        phrases = []
        for i in range(len(tokens) - n + 1):
            phrase = " ".join(tokens[i:i + n])
            phrases.append(phrase)

        freq = Counter(phrases)
        return freq.most_common(self.max_keywords)

    def extract_top_n(self, text: str, n: int = 10) -> List[str]:
        """Extract top N keywords as plain strings."""
        keywords = self.extract(text)
        return [kw.text for kw in keywords[:n]]

    def compute_term_frequency(self, text: str) -> Dict[str, float]:
        """Compute term frequency for each token in text."""
        tokens = tokenize(text, remove_stopwords=True)
        tokens = [t for t in tokens if len(t) >= self.min_length]
        if not tokens:
            return {}
        freq = Counter(tokens)
        total = len(tokens)
        return {word: count / total for word, count in freq.items()}

    def compare_keywords(self, text1: str, text2: str) -> Dict[str, float]:
        """Compare keywords between two texts, returning shared keywords with scores."""
        kw1 = {kw.text: kw.score for kw in self.extract(text1)}
        kw2 = {kw.text: kw.score for kw in self.extract(text2)}
        shared = {}
        for word in set(kw1.keys()) & set(kw2.keys()):
            shared[word] = (kw1[word] + kw2[word]) / 2
        return dict(sorted(shared.items(), key=lambda x: x[1], reverse=True))
