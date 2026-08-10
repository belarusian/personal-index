"""Search suggestions module for providing autocomplete and related queries."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass
class Suggestion:
    """A single search suggestion."""

    text: str
    score: float = 0.0
    source: str = "unknown"  # "history", "tags", "keywords", "trending"
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To_dict."""
        return {
            "text": self.text,
            "score": round(self.score, 4),
            "source": self.source,
            "category": self.category,
        }


class SearchSuggestions:
    """Generates search suggestions from indexed content metadata."""

    def __init__(
        self,
        max_suggestions: int = 10,
        min_prefix_length: int = 2,
    ):
        self.max_suggestions = max_suggestions
        self.min_prefix_length = min_prefix_length
        self._search_history: list[str] = []
        self._tags: list[str] = []
        self._keywords: list[str] = []
        self._trending: Counter = Counter()

    def add_search_history(self, queries: list[str]) -> None:
        """Add queries to search history."""
        self._search_history.extend(queries)

    def add_tags(self, tags: list[str]) -> None:
        """Add tags for suggestion generation."""
        self._tags.extend(tags)

    def add_keywords(self, keywords: list[str]) -> None:
        """Add extracted keywords for suggestion generation."""
        self._keywords.extend(keywords)

    def record_search(self, query: str) -> None:
        """Record a single search query."""
        self._search_history.append(query)
        self._trending[query.lower()] += 1

    def get_trending(self, n: int = 10) -> list[str]:
        """Get the most trending search queries."""
        return [q for q, _ in self._trending.most_common(n)]

    def suggest(self, prefix: str, sources: list[str] | None = None) -> list[Suggestion]:
        """Generate suggestions for a given prefix."""
        if len(prefix) < self.min_prefix_length:
            return []

        prefix_lower = prefix.lower()
        candidates: dict[str, Suggestion] = {}

        if not sources or "history" in sources:
            self._suggest_from_history(prefix_lower, candidates)
        if not sources or "tags" in sources:
            self._suggest_from_tags(prefix_lower, candidates)
        if not sources or "keywords" in sources:
            self._suggest_from_keywords(prefix_lower, candidates)
        if not sources or "trending" in sources:
            self._suggest_from_trending(prefix_lower, candidates)

        # Sort by score and return top N
        sorted_suggestions = sorted(candidates.values(), key=lambda s: s.score, reverse=True)
        return sorted_suggestions[: self.max_suggestions]

    def _suggest_from_history(self, prefix: str, candidates: dict[str, Suggestion]) -> None:
        """Generate suggestions from search history."""
        counts: Counter = Counter()
        for query in self._search_history:
            if query.lower().startswith(prefix):
                counts[query] += 1

        for query, count in counts.most_common(self.max_suggestions):
            score = min(count / max(len(self._search_history), 1) * 10, 1.0)
            candidates[query] = Suggestion(
                text=query,
                score=score,
                source="history",
                category="recent_search",
            )

    def _suggest_from_tags(self, prefix: str, candidates: dict[str, Suggestion]) -> None:
        """Generate suggestions from tags."""
        counts: Counter = Counter()
        for tag in self._tags:
            if tag.lower().startswith(prefix):
                counts[tag] += 1

        for tag, count in counts.most_common(self.max_suggestions):
            score = min(count / max(len(self._tags), 1) * 10, 1.0)
            candidates[tag] = Suggestion(
                text=tag,
                score=score * 0.9,  # Slightly lower priority than history
                source="tags",
                category="tag",
            )

    def _suggest_from_keywords(self, prefix: str, candidates: dict[str, Suggestion]) -> None:
        """Generate suggestions from keywords."""
        counts: Counter = Counter()
        for kw in self._keywords:
            if kw.lower().startswith(prefix):
                counts[kw] += 1

        for kw, count in counts.most_common(self.max_suggestions):
            score = min(count / max(len(self._keywords), 1) * 10, 1.0)
            candidates[kw] = Suggestion(
                text=kw,
                score=score * 0.8,
                source="keywords",
                category="keyword",
            )

    def _suggest_from_trending(self, prefix: str, candidates: dict[str, Suggestion]) -> None:
        """Generate suggestions from trending queries."""
        for query, count in self._trending.most_common(self.max_suggestions):
            if query.startswith(prefix):
                score = min(count / max(sum(self._trending.values()), 1) * 10, 1.0)
                if query not in candidates or score > candidates[query].score:
                    candidates[query] = Suggestion(
                        text=query,
                        score=score * 1.1,  # Boost trending
                        source="trending",
                        category="trending",
                    )

    def get_related_queries(self, query: str, n: int = 5) -> list[Suggestion]:
        """Get queries related to the given query (from history)."""
        words = set(re.split(r'\s+', query.lower()))
        related: dict[str, float] = {}

        for h in self._search_history:
            h_words = set(re.split(r'\s+', h.lower()))
            if h.lower() != query.lower() and h_words & words:
                overlap = len(h_words & words) / max(len(words), 1)
                related[h] = related.get(h, 0) + overlap

        sorted_related = sorted(related.items(), key=lambda x: x[1], reverse=True)
        return [
            Suggestion(text=q, score=s, source="related", category="related_query")
            for q, s in sorted_related[:n]
        ]

    def clear(self) -> None:
        """Clear all suggestion data."""
        self._search_history.clear()
        self._tags.clear()
        self._keywords.clear()
        self._trending.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize suggestion data."""
        return {
            "search_history": self._search_history,
            "tags": self._tags,
            "keywords": self._keywords,
            "trending": dict(self._trending),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchSuggestions:
        """Deserialize suggestion data."""
        instance = cls()
        instance._search_history = data.get("search_history", [])
        instance._tags = data.get("tags", [])
        instance._keywords = data.get("keywords", [])
        instance._trending = Counter(data.get("trending", {}))
        return instance
