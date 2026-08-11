"""
Content Search Module
Full-text search with ranking, filtering, and relevance scoring.
"""

from __future__ import annotations

import string
from typing import Any


class SearchIndex:
    """In-memory inverted index for full-text search."""

    def __init__(self):
        self._index: dict[str, set] = {}  # term -> set of item_ids
        self._items: dict[str, dict[str, Any]] = {}  # id -> item
        self._term_freq: dict[str, dict[str, int]] = {}  # term -> {item_id: count}

    def add_item(self, item: dict[str, Any]) -> None:
        """Add an item to the search index."""
        item_id = str(item.get("id", id(item)))
        self._items[item_id] = item
        text = self._extract_text(item)
        tokens = self._tokenize(text)
        for token in tokens:
            if token not in self._index:
                self._index[token] = set()
            self._index[token].add(item_id)
            if token not in self._term_freq:
                self._term_freq[token] = {}
            self._term_freq[token][item_id] = self._term_freq[token].get(item_id, 0) + 1

    def add_items(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            self.add_item(item)

    def remove_item(self, item_id: str) -> None:
        """Remove an item from the search index."""
        item_id = str(item_id)
        if item_id not in self._items:
            return
        item = self._items.pop(item_id)
        text = self._extract_text(item)
        tokens = self._tokenize(text)
        for token in tokens:
            if token in self._index:
                self._index[token].discard(item_id)
                if not self._index[token]:
                    del self._index[token]
            if token in self._term_freq:
                self._term_freq[token].pop(item_id, None)
                if not self._term_freq[token]:
                    del self._term_freq[token]

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search the index and return ranked results."""
        tokens = self._tokenize(query)
        if not tokens:
            return {"results": [], "total": 0, "query": query}

        # Find candidate items matching any query token
        candidates: dict[str, float] = {}
        for token in tokens:
            if token in self._index:
                for item_id in self._index[token]:
                    if item_id not in candidates:
                        candidates[item_id] = 0.0
                    # TF-based scoring
                    tf = self._term_freq.get(token, {}).get(item_id, 0)
                    candidates[item_id] += tf

        # Apply filters
        if filters:
            candidates = self._apply_filters(candidates, filters)

        # Rank by score descending
        ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)

        # Paginate
        total = len(ranked)
        page = ranked[offset:offset + limit]

        results = []
        for item_id, score in page:
            item = self._items.get(item_id)
            if item:
                results.append({
                    "item": {k: v for k, v in item.items() if k != "content"},
                    "score": round(score, 4),
                })

        return {"results": results, "total": total, "query": query}

    def _apply_filters(
        self, candidates: dict[str, float], filters: dict[str, Any]
    ) -> dict[str, float]:
        filtered = {}
        for item_id, score in candidates.items():
            item = self._items.get(item_id)
            if not item:
                continue
            if self._matches_filters(item, filters):
                filtered[item_id] = score
        return filtered

    def _matches_filters(self, item: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, value in filters.items():
            item_value = item.get(key)
            if isinstance(value, (list, set)):
                # For list filters: check if any item value matches any filter value
                if isinstance(item_value, (list, set)):
                    if not set(item_value) & set(value):
                        return False
                else:
                    if item_value not in value:
                        return False
            elif isinstance(value, dict):
                # Range filter: {"$gte": ..., "$lte": ...}
                if "$gte" in value and item_value is not None and item_value < value["$gte"]:
                    return False
                if "$lte" in value and item_value is not None and item_value > value["$lte"]:
                    return False
            else:
                if item_value != value:
                    return False
        return True

    def _extract_text(self, item: dict[str, Any]) -> str:
        parts = []
        for field in ("title", "description", "content", "tags"):
            val = item.get(field)
            if isinstance(val, list):
                parts.extend(val)
            elif isinstance(val, str):
                parts.append(val)
        return " ".join(parts)

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower()
        text = text.translate(str.maketrans("", "", string.punctuation))
        tokens = text.split()
        # Remove stop words
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "and", "but", "or", "nor", "not", "so",
            "yet", "both", "either", "neither", "each", "every", "all",
            "any", "few", "more", "most", "other", "some", "such", "no",
            "only", "own", "same", "than", "too", "very", "just", "that",
            "this", "these", "those", "it", "its", "i", "me", "my", "we",
            "our", "you", "your", "he", "him", "his", "she", "her", "they",
            "them", "their", "what", "which", "who", "whom", "where", "when",
            "why", "how", "if", "then", "else", "about", "up", "out", "off",
        }
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    @property
    def item_count(self) -> int:
        return len(self._items)

    @property
    def term_count(self) -> int:
        return len(self._index)

    def get_suggestions(self, prefix: str, limit: int = 5) -> list[str]:
        """Get autocomplete suggestions for a prefix."""
        prefix = prefix.lower()
        suggestions = []
        for term in self._index:
            if term.startswith(prefix):
                suggestions.append(term)
        suggestions.sort()
        return suggestions[:limit]

    def save_index(self, filepath):
        """Save the search index to a JSON file."""
        import json as _json
        data = {
            "items": self._items,
            "index": {k: list(v) for k, v in self._index.items()},
            "term_freq": self._term_freq,
        }
        with open(filepath, "w") as f:
            _json.dump(data, f, default=str)

    def load_index(self, filepath):
        """Load the search index from a JSON file."""
        import json as _json
        with open(filepath) as f:
            data = _json.load(f)
        self._items = data["items"]
        self._index = {k: set(v) for k, v in data["index"].items()}
        self._term_freq = data["term_freq"]





    def highlight_matches(self, text, query, marker="*"):
        """Highlight query terms in text."""
        tokens = self._tokenize(query)
        result = text
        for token in tokens:
            if token in result.lower():
                import re as _re
                pattern = _re.compile(_re.escape(token), _re.IGNORECASE)
                result = pattern.sub(f"{marker}{token}{marker}", result)
        return result


class ContentSearch:
    """High-level search interface."""

    def __init__(self):
        self.index = SearchIndex()

    def index_items(self, items: list[dict[str, Any]]) -> None:
        self.index.add_items(items)

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        result: dict[str, Any] = self.index.search(query, filters=filters, limit=limit, offset=offset)
        return result

    def remove_item(self, item_id: str) -> None:
        self.index.remove_item(item_id)

    def get_suggestions(self, prefix: str, limit: int = 5) -> list[str]:
        result: list[str] = self.index.get_suggestions(prefix, limit)
        return result
