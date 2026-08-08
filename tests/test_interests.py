"""Tests for the interests module."""

import pytest
from personal_index.interests import Interest, InterestManager


class TestInterest:
    def test_create_interest(self):
        interest = Interest(name="python", keywords=["python", "programming"])
        assert interest.name == "python"
        assert "python" in interest.keywords

    def test_matches_text_positive(self):
        interest = Interest(name="python", keywords=["python"])
        assert interest.matches_text("I love Python programming") is True

    def test_matches_text_negative(self):
        interest = Interest(name="python", keywords=["python"])
        assert interest.matches_text("I love Java programming") is False

    def test_matches_text_case_insensitive(self):
        interest = Interest(name="python", keywords=["python"])
        assert interest.matches_text("PYTHON is great") is True

    def test_matches_url_positive(self):
        interest = Interest(name="docs", url_patterns=[r"docs\.example\.com"])
        assert interest.matches_url("https://docs.example.com/page") is True

    def test_matches_url_negative(self):
        interest = Interest(name="docs", url_patterns=[r"docs\.example\.com"])
        assert interest.matches_url("https://blog.example.com/page") is False

    def test_empty_keywords_matches_all(self):
        interest = Interest(name="all")
        assert interest.matches_text("anything") is True

    def test_empty_url_patterns_matches_all(self):
        interest = Interest(name="all")
        assert interest.matches_url("https://anywhere.com") is True


class TestInterestManager:
    def test_add_interest(self):
        mgr = InterestManager()
        mgr.add_interest(Interest(name="python"))
        assert len(mgr.list_interests()) == 1

    def test_add_duplicate_raises(self):
        mgr = InterestManager()
        mgr.add_interest(Interest(name="python"))
        with pytest.raises(ValueError):
            mgr.add_interest(Interest(name="python"))

    def test_remove_interest(self):
        mgr = InterestManager()
        mgr.add_interest(Interest(name="python"))
        mgr.remove_interest("python")
        assert len(mgr.list_interests()) == 0

    def test_get_interest(self):
        mgr = InterestManager()
        mgr.add_interest(Interest(name="python"))
        assert mgr.get_interest("python").name == "python"

    def test_get_interest_not_found(self):
        mgr = InterestManager()
        assert mgr.get_interest("nonexistent") is None

    def test_matches_any(self):
        mgr = InterestManager()
        mgr.add_interest(Interest(name="python", keywords=["python"]))
        mgr.add_interest(Interest(name="java", keywords=["java"]))
        result = mgr.matches_any(text="learning python basics")
        assert "python" in result
        assert "java" not in result
