"""Content similarity detection using various algorithms."""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SimilarityResult:
    """Result of a similarity comparison."""

    score: float
    method: str
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SimilarityEngine:
    """Detects content similarity using multiple algorithms."""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    def compare(self, text1: str, text2: str, method: str = "auto") -> SimilarityResult:
        """Compare two texts for similarity."""
        if method == "auto":
            return self._best_method(text1, text2)
        elif method == "jaccard":
            return self._jaccard_similarity(text1, text2)
        elif method == "cosine":
            return self._cosine_similarity(text1, text2)
        elif method == "overlap":
            return self._overlap_coefficient(text1, text2)
        elif method == "levenshtein":
            return self._levenshtein_similarity(text1, text2)
        else:
            raise ValueError(f"Unknown method: {method}")

    def is_similar(self, text1: str, text2: str, method: str = "auto") -> bool:
        """Check if two texts are similar above threshold."""
        result = self.compare(text1, text2, method)
        return result.score >= self.threshold

    def find_duplicates(self, texts: list[str], method: str = "auto") -> list[tuple[int, int, float]]:
        """Find duplicate pairs in a list of texts."""
        duplicates = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                result = self.compare(texts[i], texts[j], method)
                if result.score >= self.threshold:
                    duplicates.append((i, j, result.score))
        return duplicates

    def _tokenize(self, text: str) -> set[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return set(text.split())

    def _jaccard_similarity(self, text1: str, text2: str) -> SimilarityResult:
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        if not tokens1 and not tokens2:
            return SimilarityResult(score=1.0, method="jaccard")
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        score = len(intersection) / len(union) if union else 0.0
        return SimilarityResult(
            score=score,
            method="jaccard",
            details={"intersection": len(intersection), "union": len(union)},
        )

    def _cosine_similarity(self, text1: str, text2: str) -> SimilarityResult:
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        all_tokens = tokens1 | tokens2
        if not all_tokens:
            return SimilarityResult(score=1.0, method="cosine")

        vec1 = [1 if t in tokens1 else 0 for t in all_tokens]
        vec2 = [1 if t in tokens2 else 0 for t in all_tokens]

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))

        if mag1 == 0 or mag2 == 0:
            return SimilarityResult(score=0.0, method="cosine")

        score = dot_product / (mag1 * mag2)
        return SimilarityResult(score=score, method="cosine")

    def _overlap_coefficient(self, text1: str, text2: str) -> SimilarityResult:
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        if not tokens1 or not tokens2:
            return SimilarityResult(score=0.0, method="overlap")
        intersection = len(tokens1 & tokens2)
        min_size = min(len(tokens1), len(tokens2))
        score = intersection / min_size
        return SimilarityResult(score=score, method="overlap")

    def _levenshtein_similarity(self, text1: str, text2: str) -> SimilarityResult:
        shorter = text1 if len(text1) <= len(text2) else text2
        longer = text2 if len(text1) <= len(text2) else text1

        if not shorter:
            return SimilarityResult(score=1.0 if not longer else 0.0, method="levenshtein")

        prev_row = list(range(len(shorter) + 1))
        for i, c1 in enumerate(longer):
            curr_row = [i + 1]
            for j, c2 in enumerate(shorter):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row

        distance = prev_row[-1]
        max_len = max(len(text1), len(text2))
        score = 1.0 - (distance / max_len) if max_len > 0 else 1.0
        return SimilarityResult(score=score, method="levenshtein", details={"distance": distance})

    def _best_method(self, text1: str, text2: str) -> SimilarityResult:
        if len(text1) < 100 and len(text2) < 100:
            return self._levenshtein_similarity(text1, text2)
        return self._cosine_similarity(text1, text2)
