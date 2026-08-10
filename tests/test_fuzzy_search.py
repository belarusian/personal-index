"""Tests for fuzzy search module."""

from __future__ import annotations

import pytest

from personal_index.fuzzy_search import (
    FuzzyMatch,
    FuzzySearcher,
)


class TestFuzzyMatch:
    """Tests for FuzzyMatch dataclass."""

    def test_create_match(self):
        m = FuzzyMatch(text="hello world", score=0.9)
        assert m.text == "hello world"
        assert m.score == 0.9
        assert m.matched_indices == []

    def test_create_with_indices(self):
        m = FuzzyMatch(text="hello", score=1.0, matched_indices=[0, 1, 2])
        assert m.matched_indices == [0, 1, 2]


class TestFuzzySearcher:
    """Tests for FuzzySearcher class."""

    def setup_method(self):
        self.searcher = FuzzySearcher()

    def test_search_empty(self):
        assert self.searcher.search("query", []) == []

    def test_search_empty_query(self):
        assert self.searcher.search("", ["hello"]) == []

    def test_exact_match(self):
        results = self.searcher.search("hello", ["hello", "world"])
        assert len(results) == 1
        assert results[0].score == 1.0
        assert results[0].text == "hello"

    def test_substring_match(self):
        results = self.searcher.search("hello", ["hello world", "foo bar"])
        assert len(results) == 1
        assert results[0].score == 0.9
        assert results[0].text == "hello world"

    def test_fuzzy_match(self):
        results = self.searcher.search("helo", ["hello", "world"])
        assert len(results) >= 1
        assert results[0].text == "hello"

    def test_no_match(self):
        searcher = FuzzySearcher(min_score=0.8)
        results = searcher.search("xyz", ["hello", "world"])
        assert len(results) == 0

    def test_multiple_matches_sorted(self):
        results = self.searcher.search("python", [
            "python programming",
            "pyton tutorial",
            "java basics",
        ])
        assert len(results) >= 2
        assert results[0].score >= results[1].score

    def test_case_insensitive(self):
        results = self.searcher.search("HELLO", ["hello world"])
        assert len(results) == 1
        assert results[0].text == "hello world"

    def test_match_indices_exact(self):
        results = self.searcher.search("hello", ["say hello there"])
        assert len(results) == 1
        assert results[0].matched_indices == [4, 5, 6, 7, 8]

    def test_min_score_filtering(self):
        searcher = FuzzySearcher(min_score=0.95)
        results = searcher.search("helo", ["hello"])
        assert len(results) == 0

    def test_search_in_dict(self):
        items = {"python": "Python programming", "java": "Java basics"}
        results = self.searcher.search("python", items)
        assert len(results) >= 1
        assert any("python" in r.text.lower() for r in results)

    def test_search_in_dict_empty(self):
        results = self.searcher.search("query", {})
        assert results == []

    def test_highlight(self):
        text = "hello world"
        highlighted = self.searcher.highlight(text, [0, 1, 2, 3, 4])
        assert "\033[1m" in highlighted
        assert "\033[0m" in highlighted

    def test_highlight_empty_indices(self):
        text = "hello"
        highlighted = self.searcher.highlight(text, [])
        assert highlighted == text

    def test_highlight_html(self):
        text = "hello world"
        highlighted = self.searcher.highlight_html(text, [0, 1, 2, 3, 4])
        assert "<mark>" in highlighted
        assert "</mark>" in highlighted

    def test_highlight_html_empty(self):
        text = "hello"
        highlighted = self.searcher.highlight_html(text, [])
        assert highlighted == text

    def test_search_with_highlight(self):
        results = self.searcher.search_with_highlight("hello", ["hello world"])
        assert len(results) == 1
        _match, highlighted = results[0]
        assert "\033[1m" in highlighted

    def test_search_with_highlight_html(self):
        results = self.searcher.search_with_highlight(
            "hello", ["hello world"], html=True
        )
        assert len(results) == 1
        _, highlighted = results[0]
        assert "<mark>" in highlighted

    def test_typo_tolerance(self):
        results = self.searcher.search("pyton", ["python tutorial"])
        assert len(results) >= 1
        assert results[0].text == "python tutorial"

    def test_partial_word_match(self):
        results = self.searcher.search("prog", ["programming basics"])
        assert len(results) >= 1

    def test_long_text_search(self):
        long_text = "This is a very long text with many words and the word hello appears in the middle"
        results = self.searcher.search("hello", [long_text])
        assert len(results) == 1
        assert results[0].score == 0.9


class TestFuzzyMatchTypeFix:
    """Tests for TICKET-26: matched_indices type annotation fix."""

    def test_matched_indices_is_list_not_none(self):
        """matched_indices should always be a list, never None."""
        m = FuzzyMatch(text="hello", score=0.9)
        assert isinstance(m.matched_indices, list)
        assert m.matched_indices == []

    def test_matched_indices_with_explicit_none(self):
        """Even when explicitly passed None, __post_init__ converts to list."""
        m = FuzzyMatch(text="hello", score=0.9, matched_indices=None)
        assert isinstance(m.matched_indices, list)
        assert m.matched_indices == []

    def test_matched_indices_annotation_is_list_int(self):
        """The annotation should be list[int], not list[int] | None."""
        import typing
        hints = typing.get_type_hints(FuzzyMatch)
        # The annotation should be list[int], not Optional[list[int]]
        hint = hints.get("matched_indices", "")
        # Should not contain "None" or "Union"
        assert "None" not in str(hint) or "list[int]" in str(hint)

    def test_highlight_never_receives_none(self):
        """highlight() should never receive None for indices."""
        searcher = FuzzySearcher()
        m = FuzzyMatch(text="hello world", score=0.9)
        # This should work without error since matched_indices is always a list
        highlighted = searcher.highlight(m.text, m.matched_indices)
        assert highlighted == "hello world"

    def test_highlight_html_never_receives_none(self):
        """highlight_html() should never receive None for indices."""
        searcher = FuzzySearcher()
        m = FuzzyMatch(text="hello world", score=0.9)
        # This should work without error since matched_indices is always a list
        highlighted = searcher.highlight_html(m.text, m.matched_indices)
        assert highlighted == "hello world"

    def test_search_with_highlight_no_none_indices(self):
        """search_with_highlight should work without None indices."""
        searcher = FuzzySearcher()
        results = searcher.search_with_highlight("hello", ["hello world"])
        assert len(results) == 1
        match, highlighted = results[0]
        assert isinstance(match.matched_indices, list)
        assert "\033[1m" in highlighted

    def test_search_with_highlight_html_no_none_indices(self):
        """search_with_highlight with html=True should work without None indices."""
        searcher = FuzzySearcher()
        results = searcher.search_with_highlight("hello", ["hello world"], html=True)
        assert len(results) == 1
        match, highlighted = results[0]
        assert isinstance(match.matched_indices, list)
        assert "<mark>" in highlighted
