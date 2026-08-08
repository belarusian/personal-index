"""Tests for the content filtering module."""

import pytest
from personal_index.interests import Interest, InterestStore
from personal_index.filter import ContentFilter, FilterResult


@pytest.fixture
def interest_store(tmp_path):
    store = InterestStore(store_path=str(tmp_path / "interests.json"))
    store.add(Interest(
        name="python",
        keywords=["python", "programming", "developer"],
        url_patterns=[r"https://python\.org/.*"],
        topics=["coding"],
        priority=3,
    ))
    store.add(Interest(
        name="ai",
        keywords=["artificial intelligence", "machine learning", "neural network"],
        url_patterns=[r"https://ai\.example\.com/.*"],
        topics=["AI", "ML"],
        priority=5,
    ))
    return store


class TestFilterResult:
    def test_default_values(self):
        result = FilterResult(matched=False)
        assert result.matched is False
        assert result.score == 0.0
        assert result.matching_interests == []

    def test_custom_values(self):
        result = FilterResult(matched=True, score=1.5, matching_interests=["test"])
        assert result.matched is True
        assert result.score == 1.5


class TestContentFilter:
    def test_filter_url_match(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.filter_url("https://python.org/docs")
        assert result.matched is True
        assert result.score > 0

    def test_filter_url_no_match(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.filter_url("https://random-site.com/page")
        assert result.matched is False

    def test_filter_content_keywords(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.filter_content("Learn Python programming today")
        assert result.matched is True
        assert "python" in result.matched_keywords
        assert "programming" in result.matched_keywords

    def test_filter_content_no_match(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.filter_content("This is about cooking recipes")
        assert result.matched is False

    def test_filter_content_case_insensitive(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.filter_content("PYTHON is great for PROGRAMMING")
        assert result.matched is True

    def test_should_index_url_match(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.should_index("https://python.org/about", "Python", "")
        assert result.matched is True

    def test_should_index_content_match(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.should_index(
            "https://example.com/blog",
            "Python Tips",
            "Learn Python programming"
        )
        assert result.matched is True

    def test_should_index_no_match(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.should_index(
            "https://example.com/blog",
            "Cooking Tips",
            "Learn to cook pasta"
        )
        assert result.matched is False

    def test_score_calculation(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.filter_content("Python Python Python")
        assert result.score > 0

    def test_multiple_interests_match(self, interest_store):
        filter = ContentFilter(interest_store)
        result = filter.filter_content(
            "Python and artificial intelligence are both interesting"
        )
        assert result.matched is True
        assert len(result.matching_interests) >= 1

    def test_empty_interest_store(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        filter = ContentFilter(store)
        result = filter.filter_content("Some random text")
        assert result.matched is False
