"""
Content Search Module
Full-text search with ranking, filtering, and relevance scoring.
"""

from __future__ import annotations

import math
import re
import string
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Snippet:
    """A highlighted text snippet from a search result."""

    text: str
    highlighted: str
    start_offset: int = 0
    end_offset: int = 0
    matched_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "highlighted": self.highlighted,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "matched_terms": self.matched_terms,
        }


class SnippetExtractor:
    """Extracts and highlights relevant snippets from search results."""

    def __init__(
        self,
        max_snippet_length: int = 200,
        max_snippets: int = 3,
        ellipsis: str = "...",
        marker_open: str = "<mark>",
        marker_close: str = "</mark>",
    ):
        self.max_snippet_length = max_snippet_length
        self.max_snippets = max_snippets
        self.ellipsis = ellipsis
        self.marker_open = marker_open
        self.marker_close = marker_close

    def extract(
        self,
        text: str,
        query_terms: list[str],
    ) -> list[Snippet]:
        """Extract highlighted snippets from text matching query terms.

        Finds the most relevant portions of text containing query terms
        and returns them as highlighted snippets.
        """
        if not text or not query_terms:
            return []

        text_lower = text.lower()
        # Find all positions of all query terms
        all_positions: list[tuple[int, int, str]] = []  # (start, end, term)
        for term in query_terms:
            term_lower = term.lower()
            start = 0
            while start < len(text_lower):
                pos = text_lower.find(term_lower, start)
                if pos == -1:
                    break
                all_positions.append((pos, pos + len(term), term))
                start = pos + 1

        if not all_positions:
            # No matches found, return first portion of text
            return self._make_fallback_snippet(text)

        # Sort by position
        all_positions.sort(key=lambda x: x[0])

        # Group nearby matches into snippet windows
        snippets = self._group_into_windows(text, all_positions)

        return snippets[: self.max_snippets]

    def _group_into_windows(
        self,
        text: str,
        positions: list[tuple[int, int, str]],
    ) -> list[Snippet]:
        """Group match positions into snippet windows."""
        if not positions:
            return []

        # Calculate half window size
        half_window = self.max_snippet_length // 2

        # Group positions that are within the window of each other
        groups: list[list[tuple[int, int, str]]] = []
        current_group: list[tuple[int, int, str]] = [positions[0]]

        for pos in positions[1:]:
            # If this position is within window of the last in group
            if pos[0] - current_group[-1][0] <= self.max_snippet_length:
                current_group.append(pos)
            else:
                groups.append(current_group)
                current_group = [pos]
        groups.append(current_group)

        snippets = []
        for group in groups:
            snippet = self._make_snippet(text, group, half_window)
            if snippet:
                snippets.append(snippet)

        return snippets

    def _make_snippet(
        self,
        text: str,
        positions: list[tuple[int, int, str]],
        half_window: int,
    ) -> Snippet | None:
        """Create a single snippet from a group of match positions."""
        first_start = positions[0][0]
        last_end = positions[-1][1]
        window_start, window_end = self._calc_window(text, first_start, last_end, half_window)
        snippet_text = text[window_start:window_end]
        matched_terms = list({term for _, _, term in positions})
        highlighted = self._highlight_terms(snippet_text, matched_terms)
        prefix = self.ellipsis if window_start > 0 else ""
        suffix = self.ellipsis if window_end < len(text) else ""
        return Snippet(
            text=snippet_text,
            highlighted=f"{prefix}{highlighted}{suffix}",
            start_offset=window_start,
            end_offset=window_end,
            matched_terms=matched_terms,
        )

    @staticmethod
    def _calc_window(text: str, first_start: int, last_end: int, half: int) -> tuple[int, int]:
        """Calculate window boundaries with word boundary adjustment."""
        ws = max(0, first_start - half)
        we = min(len(text), last_end + half)
        if ws > 0:
            sp = text.rfind(" ", 0, ws)
            if sp != -1:
                ws = sp + 1
        if we < len(text):
            sp = text.find(" ", we)
            if sp != -1:
                we = sp
        return ws, we

    def _highlight_terms(self, text: str, terms: list[str]) -> str:
        """Highlight query terms in text."""
        if not terms:
            return text

        # Sort terms by length (longest first) to avoid partial replacements
        sorted_terms = sorted(terms, key=len, reverse=True)
        result = text

        for term in sorted_terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            result = pattern.sub(
                f"{self.marker_open}\\g<0>{self.marker_close}",
                result,
            )

        return result

    def _make_fallback_snippet(self, text: str) -> list[Snippet]:
        """Create a fallback snippet when no terms match."""
        if len(text) <= self.max_snippet_length:
            return [Snippet(text=text, highlighted=text)]

        snippet_text = text[:self.max_snippet_length]
        # Try to break at word boundary
        last_space = snippet_text.rfind(" ")
        if last_space > self.max_snippet_length * 0.5:
            snippet_text = snippet_text[:last_space]

        return [
            Snippet(
                text=snippet_text,
                highlighted=f"{snippet_text}{self.ellipsis}",
            )
        ]

    def highlight_text(
        self,
        text: str,
        terms: list[str],
    ) -> str:
        """Simply highlight terms in text without snippet extraction."""
        return self._highlight_terms(text, terms)


class SearchIndex:
    """In-memory inverted index for full-text search."""

    def __init__(self):
        self._index: dict[str, set] = {}  # term -> set of item_ids
        self._items: dict[str, dict[str, Any]] = {}  # id -> item
        self._term_freq: dict[str, dict[str, int]] = {}  # term -> {item_id: count}
        self._doc_lengths: dict[str, int] = {}  # item_id -> total token count
        self._snippet_extractor = SnippetExtractor()

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

    def _find_candidates(self, tokens: list[str]) -> dict[str, float]:
        cands: dict[str, float] = {}
        for token in tokens:
            if token in self._index:
                for item_id in self._index[token]:
                    if item_id not in cands:
                        cands[item_id] = 0.0
        return cands

    def _score_candidates(self, cands: dict[str, float], tokens: list[str], ranking: str) -> dict[str, float]:
        if ranking == "tfidf":
            return self._score_tfidf(cands, tokens)
        if ranking == "bm25":
            return self._score_bm25(cands, tokens)
        for token in tokens:
            for item_id in self._index.get(token, set()):
                cands[item_id] += self._term_freq.get(token, {}).get(item_id, 0)
        return cands

    def _build_entry(self, item: dict[str, Any], score: float, tokens: list[str], highlight: bool) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "item": {k: v for k, v in item.items() if k != "content"},
            "score": round(score, 4),
        }
        if highlight:
            content = item.get("content", "") or item.get("description", "") or ""
            snippets = self._snippet_extractor.extract(content, tokens)
            entry["snippets"] = [s.to_dict() for s in snippets]
        return entry

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        ranking: str = "tf",
        highlight: bool = False,
    ) -> dict[str, Any]:
        """Search the index and return ranked results.

        Tokenizes the query (lowercase, punctuation stripped, stop-words and
        single characters dropped). If no tokens remain, returns exactly
        {"results": [], "total": 0, "query": query} without touching the index.

        Otherwise finds candidate items, scores them with the requested
        ranking ("tf" default = summed term frequency, "tfidf", or "bm25"),
        optionally narrows them with `filters`, sorts by score descending,
        and returns a dict with:
          - "results": the offset:offset+limit page of entries, each a dict
            with "item" (the stored item with its "content" key removed) and
            "score" (rounded to 4 decimals); when highlight=True each entry
            also carries "snippets" (list of Snippet.to_dict() dicts), and the
            key is absent when highlight=False.
          - "total": len(ranked) = the count of ALL ranked candidates BEFORE
            the offset/limit page slice, so it can exceed len(results).
          - "query": the original query string, echoed back unchanged.
        """
        tokens = self._tokenize(query)
        if not tokens:
            return {"results": [], "total": 0, "query": query}

        cands = self._find_candidates(tokens)
        cands = self._score_candidates(cands, tokens, ranking)
        if filters:
            cands = self._apply_filters(cands, filters)

        ranked = sorted(cands.items(), key=lambda x: x[1], reverse=True)
        page = ranked[offset:offset + limit]
        results = []
        for item_id, score in page:
            item = self._items.get(item_id)
            if item:
                results.append(self._build_entry(item, score, tokens, highlight))

        return {"results": results, "total": len(ranked), "query": query}

    def _score_tfidf(
        self,
        candidates: dict[str, float],
        query_tokens: list[str],
    ) -> dict[str, float]:
        """Score candidates using TF-IDF."""
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
        """Score candidates using BM25 algorithm."""
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
                if isinstance(item_value, (list, set)):
                    if not set(item_value) & set(value):
                        return False
                else:
                    if item_value not in value:
                        return False
            elif isinstance(value, dict):
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
        for key in ("title", "description", "content", "tags"):
            val = item.get(key)
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
            try:
                data = _json.load(f)
            except _json.JSONDecodeError:
                return
        if not isinstance(data, dict):
            return
        self._items = data["items"]
        self._index = {k: set(v) for k, v in data["index"].items()}
        self._term_freq = data["term_freq"]
        self._doc_lengths = data.get("doc_lengths", {})
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
                pattern = re.compile(re.escape(token), re.IGNORECASE)
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
        highlight: bool = False,
    ) -> dict[str, Any]:
        result: dict[str, Any] = self.index.search(
            query, filters=filters, limit=limit, offset=offset,
            ranking=ranking, highlight=highlight,
        )
        return result

    def remove_item(self, item_id: str) -> None:
        self.index.remove_item(item_id)

    def get_suggestions(self, prefix: str, limit: int = 5) -> list[str]:
        result: list[str] = self.index.get_suggestions(prefix, limit)
        return result
