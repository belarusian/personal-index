"""Fuzzy search for personal index."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class FuzzyMatch:
    """Result of a fuzzy search match."""
    text: str
    score: float
    matched_indices: list[int] = field(default_factory=list)

    def __post_init__(self):
        if self.matched_indices is None:
            self.matched_indices = []


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings.

    Uses the Wagner-Fischer algorithm with O(min(len(s1), len(s2))) space.
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    # Ensure s1 is the shorter string for memory efficiency
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    prev_row = list(range(len(s1) + 1))
    for j, c2 in enumerate(s2, 1):
        curr_row = [j]
        for i, c1 in enumerate(s1, 1):
            if c1 == c2:
                curr_row.append(prev_row[i - 1])
            else:
                curr_row.append(1 + min(
                    prev_row[i],      # deletion
                    curr_row[i - 1],  # insertion
                    prev_row[i - 1],  # substitution
                ))
        prev_row = curr_row

    return prev_row[-1]


def levenshtein_similarity(s1: str, s2: str) -> float:
    """Compute similarity score (0.0 to 1.0) based on Levenshtein distance.

    Returns 1.0 for identical strings, 0.0 for completely different strings.
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return 1.0 - (distance / max_len)


class FuzzySearcher:
    """Perform fuzzy string matching for search queries."""

    def __init__(self, min_score: float = 0.4):
        self.min_score = min_score

    def search(self, query: str, texts: list[str]) -> list[FuzzyMatch]:
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

    def search_in_dict(self, query: str, items: dict[str, str]) -> list[FuzzyMatch]:
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

        # Use Levenshtein similarity for edit-distance based scoring
        lev_score = levenshtein_similarity(query, text)

        # Use SequenceMatcher for overall similarity
        ratio = SequenceMatcher(None, query, text).ratio()

        # Take the better of Levenshtein and SequenceMatcher
        score = max(lev_score, ratio)

        # Boost if query starts match text
        if text.startswith(query[:max(1, len(query) // 2)]):
            score = max(score, 0.7)

        return score

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

    def _find_match_indices(self, query: str, text: str) -> list[int]:
        """Find indices in text that match the query."""
        indices = []
        if query in text:
            start = text.index(query)
            indices = list(range(start, start + len(query)))
        else:
            # Find best matching substring
            best_start = 0
            best_len: float = 0.0
            for i in range(len(text) - len(query) + 1):
                substring = text[i:i + len(query)]
                ratio = SequenceMatcher(None, query, substring).ratio()
                if ratio > best_len:
                    best_len = ratio
                    best_start = i
            if best_len > 0.5:
                indices = list(range(best_start, best_start + len(query)))
        return indices

    def highlight(self, text: str, indices: list[int]) -> str:
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

    def highlight_html(self, text: str, indices: list[int]) -> str:
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

    def search_with_highlight(self, query: str, texts: list[str],
                              html: bool = False) -> list[tuple[FuzzyMatch, str]]:
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
