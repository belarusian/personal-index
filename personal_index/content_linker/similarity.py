"""Similarity engine for finding related content items."""

from __future__ import annotations

import re
from typing import Any


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    if not text:
        return []
    return re.findall(r"[a-z0-9]+", text.lower())


class SimilarityEngine:
    """Computes similarity between text items using token overlap."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], float] = {}

    def similarity(self, text_a: str, text_b: str) -> float:
        """Compute a similarity score between two texts, in [0.0, 1.0].

        Contract:

          * empty input -- if ``text_a`` or ``text_b`` is falsy (an empty
            string), the score is ``0.0`` and no cache entry is written.
            A whitespace-only string is truthy, so it falls through to the
            no-token guard below and also scores ``0.0``.
          * cache -- the lookup key is the SYMMETRIC pair
            ``(min(text_a, text_b), max(text_a, text_b))`` of the RAW
            (un-tokenized) strings, so ``similarity(a, b)`` and
            ``similarity(b, a)`` share one entry.
          * no-token guard -- after tokenization, if either side yields no
            ``[a-z0-9]+`` tokens, the score is ``0.0``.
          * score -- the Jaccard index of the token sets:
            ``len(tokens_a & tokens_b) / len(tokens_a | tokens_b)``.
        """
        if not text_a or not text_b:
            return 0.0

        cache_key = (min(text_a, text_b), max(text_a, text_b))
        if cache_key in self._cache:
            return self._cache[cache_key]

        tokens_a = set(_tokenize(text_a))
        tokens_b = set(_tokenize(text_b))

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b

        score = len(intersection) / len(union) if union else 0.0
        self._cache[cache_key] = score
        return score

    def find_similar(
        self,
        query: str,
        items: list[tuple[str, str]],
        threshold: float = 0.1,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find items whose content is similar to ``query``.

        Contract:

          * each ``(item_id, content)`` pair is scored with
            ``similarity(query, content)`` and kept iff the score is
            ``>= threshold`` (inclusive).
          * kept items are sorted by score DESCENDING.
          * the list is truncated to the first ``limit`` entries.
          * each result is a dict with exactly the keys ``"id"`` (the
            item id) and ``"score"`` (the float similarity).
        """
        results: list[dict[str, Any]] = []
        for item_id, content in items:
            score = self.similarity(query, content)
            if score >= threshold:
                results.append({"id": item_id, "score": score})

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]
