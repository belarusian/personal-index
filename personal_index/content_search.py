"""
Content Search Module
Full-text search with ranking, filtering, and relevance scoring.
"""

from __future__ import annotations

import math
import string
from typing import Any


class SearchIndex:
    """In-memory inverted index for full-text search."""

    def __init__(self):
        self._index: dict[str, set] = {}  # term -> set of item_ids
        self._items: dict[str, dict[str, Any]] = {}  # id -> item
        self._term_freq: dict[str, dict[str, int]] = {}  # term -> {item_id: count}
        self._doc_lengths: dict[str, int] = {}  # item_id -> total token count

    def add_item(self, item: dict[str, Any]) -> None:
        """Add an item to the search index."""
        item_id = str(item.get("id", id(item)))
        self._items[item_id] = item
        text = self._extract_text(item)
        tokens = self._tokenize(text)
        self._doc_lengths[item_id] = len(tokens)
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
        self._doc_lengths.pop(item_id, None)

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        ranking: str = "tf",
    ) -> dict[str, Any]:
        """Search the index and return ranked results.

        Args:
            query: Search query string.
            filters: Optional filter dict.
            limit: Max results to return.
            offset: Pagination offset.
            ranking: Ranking algorithm - "tf", "tfidf", or "bm25".
        """
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

        # Score candidates using selected ranking algorithm
        if ranking == "tfidf":
            candidates = self._score_tfidf(candidates, tokens)
        elif ranking == "bm25":
            candidates = self._score_bm25(candidates, tokens)
        else:
            # Default TF-based scoring
            for token in tokens:
                for item_id in self._index.get(token, set()):
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

    def _score_tfidf(
        self,
        candidates: dict[str, float],
        query_tokens: list[str],
    ) -> dict[str, float]:
        """Score candidates using TF-IDF.

        TF-IDF = TF * IDF where:
        - TF = term frequency in document
        - IDF = log(N / df) where N = total docs, df = doc frequency of term
        """
        n_docs = max(len(self._items), 1)
        scores: dict[str, float] = {item_id: 0.0 for item_id in candidates}

        for token in query_tokens:
            if token not in self._index:
                continue
            df = len(self._index[token])
            idf = math.log(n_docs / max(df, 1))

            for item_id in self._index[token]:
                if item_id not in scores:
                    continue
                tf = self._term_freq.get(token, {}).get(item_id, 0)
                doc_len = max(self._doc_lengths.get(item_id, 1), 1)
                # Normalized TF: tf / doc_length
                norm_tf = tf / doc_len
                scores[item_id] += norm_tf * idf

        return scores

    def _score_bm25(
        self,
        candidates: dict[str, float],
        query_tokens: list[str],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> dict[str, float]:
        """Score candidates using BM25 algorithm.

        BM25 = IDF * (TF * (k1 + 1)) / (TF + k1 * (1 - b + b * avgdl))

        Args:
            candidates: Candidate item IDs.
            query_tokens: Tokenized query.
            k1: Term frequency saturation parameter (default 1.5).
            b: Document length normalization parameter (default 0.75).
        """
        n_docs = max(len(self._items), 1)
        avgdl = sum(self._doc_lengths.values()) / n_docs if self._doc_lengths else 1.0
        scores: dict[str, float] = {item_id: 0.0 for item_id in candidates}

        for token in query_tokens:
            if token not in self._index:
                continue
            df = len(self._index[token])
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)

            for item_id in self._index[token]:
                if item_id not in scores:
                    continue
                tf = self._term_freq.get(token, {}).get(item_id, 0)
                doc_len = self._doc_lengths.get(item_id, avgdl)

                # BM25 scoring formula
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / avgdl))
                scores[item_id] += idf * (numerator / denominator)

        return scores

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
                for v in val:
                    if isinstance(v, str):
                        parts.append(v)
                    elif hasattr(v, "name"):
                        parts.append(v.name)
                    else:
                        parts.append(str(v))
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
            "doc_lengths": self._doc_lengths,
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
        self._doc_lengths = data.get("doc_lengths", {})
        # Rebuild doc_lengths if not present
        if not self._doc_lengths:
            for item_id, item in self._items.items():
                text = self._extract_text(item)
                tokens = self._tokenize(text)
                self._doc_lengths[item_id] = len(tokens)

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
        ranking: str = "tf",
    ) -> dict[str, Any]:
        result: dict[str, Any] = self.index.search(
            query, filters=filters, limit=limit, offset=offset, ranking=ranking
        )
        return result

    def remove_item(self, item_id: str) -> None:
        self.index.remove_item(item_id)

    def get_suggestions(self, prefix: str, limit: int = 5) -> list[str]:
        result: list[str] = self.index.get_suggestions(prefix, limit)
        return result
