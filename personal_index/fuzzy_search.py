"""Fuzzy search for personal index."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Tuple


@dataclass
class FuzzyMatch:
    """Result of a fuzzy search match."""
    text: str
    score: float
    matched_indices: List[int] = None

    def __post_init__(self):
        if self.matched_indices is None:
            self.matched_indices = []


class FuzzySearcher:
    """Perform fuzzy string matching for search queries."""

    def __init__(self, min_score: float = 0.4):
        self.min_score = min_score

    def search(self, query: str, texts: List[str]) -> List[FuzzyMatch]:
        """Search for query in a list of texts, returning fuzzy matches."""
        if not query or not texts:
            return []

        results = []
        query_lower = query.lower()

        for text in texts:
            score = self._compute_score(query_lower, text.lower())
            if score >= self.min_score:
                indices = self._find_match_indices(query_lower, text.lower())
                results.append(FuzzyMatch(
                    text=text,
                    score=score,
                    matched_indices=indices,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def search_in_dict(self, query: str, items: Dict[str, str]) -> List[FuzzyMatch]:
        """Search in both keys and values of a dictionary."""
        all_texts = list(items.keys()) + list(items.values())
        seen = set()
        results = []

        for text in all_texts:
            if text in seen:
                continue
            seen.add(text)
            score = self._compute_score(query.lower(), text.lower())
            if score >= self.min_score:
                indices = self._find_match_indices(query.lower(), text.lower())
                results.append(FuzzyMatch(
                    text=text,
                    score=score,
                    matched_indices=indices,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _compute_score(self, query: str, text: str) -> float:
        """Compute fuzzy match score between query and text."""
        if not query or not text:
            return 0.0

        # Exact match
        if query == text:
            return 1.0

        # Check if query is a substring
        if query in text:
            return 0.9

        # Check character-by-character match (for typos)
        char_score = self._char_match_score(query, text)
        if char_score > 0:
            return char_score

        # Use SequenceMatcher for overall similarity
        ratio = SequenceMatcher(None, query, text).ratio()

        # Boost if query starts match text
        if text.startswith(query[:max(1, len(query) // 2)]):
            ratio = max(ratio, 0.7)

        return ratio

    def _char_match_score(self, query: str, text: str) -> float:
        """Score based on character-by-character matching (handles typos)."""
        if len(query) > len(text):
            return 0.0

        # Check if all query chars appear in text in order
        text_idx = 0
        matched = 0
        for q_char in query:
            found = False
            while text_idx < len(text):
                if text[text_idx] == q_char:
                    matched += 1
                    text_idx += 1
                    found = True
                    break
                text_idx += 1
            if not found:
                return 0.0

        if matched == len(query):
            return 0.85

        return 0.0

    def _find_match_indices(self, query: str, text: str) -> List[int]:
        """Find indices in text that match the query."""
        indices = []
        if query in text:
            start = text.index(query)
            indices = list(range(start, start + len(query)))
        else:
            # Find best matching substring
            best_start = 0
            best_len = 0
            for i in range(len(text) - len(query) + 1):
                substring = text[i:i + len(query)]
                ratio = SequenceMatcher(None, query, substring).ratio()
                if ratio > best_len:
                    best_len = ratio
                    best_start = i
            if best_len > 0.5:
                indices = list(range(best_start, best_start + len(query)))
        return indices

    def highlight(self, text: str, indices: List[int]) -> str:
        """Create highlighted version of text with matched indices."""
        if not indices:
            return text

        result = []
        idx_set = set(indices)
        for i, char in enumerate(text):
            if i in idx_set:
                result.append(f"\033[1m{char}\033[0m")
            else:
                result.append(char)
        return "".join(result)

    def highlight_html(self, text: str, indices: List[int]) -> str:
        """Create HTML-highlighted version of text."""
        if not indices:
            return text

        result = []
        idx_set = set(indices)
        for i, char in enumerate(text):
            if i in idx_set:
                result.append(f"<mark>{char}</mark>")
            else:
                result.append(char)
        return "".join(result)

    def search_with_highlight(self, query: str, texts: List[str],
                              html: bool = False) -> List[Tuple[FuzzyMatch, str]]:
        """Search and return matches with highlighted text."""
        matches = self.search(query, texts)
        results = []
        for match in matches:
            if html:
                highlighted = self.highlight_html(match.text, match.matched_indices)
            else:
                highlighted = self.highlight(match.text, match.matched_indices)
            results.append((match, highlighted))
        return results
