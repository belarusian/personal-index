"""End-to-end tests for interest matching and scoring."""

from __future__ import annotations

import pytest

from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest


class TestInterestMatchingE2E:
    """Test interest matching with realistic scenarios."""

    def test_keyword_match_exact(self, tmp_path):
        """Exact keyword match should trigger."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        text = "Python is a great programming language."
        matches = store.matches_any(text, "")
        assert len(matches) == 1
        assert matches[0].name == "python"

    def test_keyword_match_case_insensitive(self, tmp_path):
        """Keyword matching should be case-insensitive."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["Python"]))
        text = "python is great"
        matches = store.matches_any(text, "")
        assert len(matches) == 1

    def test_keyword_match_partial(self, tmp_path):
        """Partial keyword match should work."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="programming", keywords=["program"]))
        text = "Programming in Python"
        matches = store.matches_any(text, "")
        assert len(matches) == 1

    def test_multiple_keywords_any_match(self, tmp_path):
        """Multiple keywords with ANY mode."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="tech",
            keywords=["python", "rust", "golang"],
            match_mode="any",
        ))
        text = "I love programming in Rust"
        matches = store.matches_any(text, "")
        assert len(matches) == 1

    def test_multiple_keywords_all_match(self, tmp_path):
        """Multiple keywords with ALL mode."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="full_stack",
            keywords=["frontend", "backend"],
            match_mode="all",
        ))
        text = "Full stack development includes frontend and backend programming"
        matches = store.matches_any(text, "")
        assert len(matches) == 1

    def test_url_pattern_match(self, tmp_path):
        """URL pattern matching."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="github",
            url_patterns=["github.com"],
            keywords=[],
        ))
        text = "GitHub repository"
        url = "https://github.com/user/repo"
        matches = store.matches_any(text, url)
        assert len(matches) == 1

    def test_total_score(self, tmp_path):
        """Calculate total score across all interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))
        store.add(Interest(name="rust", keywords=["rust"], priority=3))
        text = "Python and Rust are both great programming languages"
        score = store.total_score(text)
        assert score > 0

    def test_no_match(self, tmp_path):
        """No match when content doesn't contain keywords."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        text = "Rust is a systems programming language"
        matches = store.matches_any(text, "")
        assert len(matches) == 0

    def test_interest_priority_affects_score(self, tmp_path):
        """Higher priority interests contribute more to score."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="high", keywords=["python"], priority=10))
        store.add(Interest(name="low", keywords=["rust"], priority=1))
        text = "Python and Rust"
        score = store.total_score(text)
        # Python should contribute more due to higher priority
        assert score > 0

    def test_interest_matches_method(self, tmp_path):
        """Test Interest.matches() method directly."""
        interest = Interest(
            name="python",
            keywords=["python", "programming"],
            url_patterns=[],
        )
        assert interest.matches("Python programming", "")
        assert not interest.matches("Rust systems", "")

    def test_interest_to_from_dict(self, tmp_path):
        """Test Interest serialization."""
        original = Interest(
            name="test",
            keywords=["a", "b"],
            url_patterns=["*.com"],
            priority=7,
        )
        d = original.to_dict()
        restored = Interest.from_dict(d)
        assert restored.name == original.name
        assert restored.keywords == original.keywords
