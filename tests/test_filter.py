"""Tests for content filtering."""

import pytest
from personal_index.filter import ContentFilter
from personal_index.models import Interest, IndexedPage


@pytest.fixture
def interests():
    return [
        Interest(name="python", keywords=["python", "cpython"], url_patterns=["*.python.org/*"], topics=["programming"]),
        Interest(name="rust", keywords=["rust", "cargo"], url_patterns=["*.rust-lang.org/*"], topics=["systems"]),
        Interest(name="disabled", keywords=["disabled"], enabled=False),
    ]


@pytest.fixture
def filter_(interests):
    return ContentFilter(interests)


class TestContentFilterURL:
    def test_matches_url_pattern(self, filter_):
        matched = filter_.matches_url("https://docs.python.org/3/library")
        assert "python" in matched

    def test_no_url_match(self, filter_):
        matched = filter_.matches_url("https://example.com/page")
        assert matched == []

    def test_matches_multiple_patterns(self, filter_):
        matched = filter_.matches_url("https://www.rust-lang.org/tools/install")
        assert "rust" in matched

    def test_disabled_interest_not_matched(self, filter_):
        matched = filter_.matches_url("https://example.com/disabled")
        assert "disabled" not in matched


class TestContentFilterKeywords:
    def test_matches_keyword_in_content(self, filter_):
        matched = filter_.matches_keywords("I love python programming")
        assert "python" in matched

    def test_matches_keyword_in_title(self, filter_):
        matched = filter_.matches_keywords("", title="Rust Programming")
        assert "rust" in matched

    def test_no_keyword_match(self, filter_):
        matched = filter_.matches_keywords("Hello world", title="Welcome")
        assert matched == []

    def test_keyword_case_insensitive(self, filter_):
        matched = filter_.matches_keywords("I love PYTHON")
        assert "python" in matched

    def test_disabled_keyword_not_matched(self, filter_):
        matched = filter_.matches_keywords("This is disabled")
        assert "disabled" not in matched


class TestContentFilterTopics:
    def test_matches_topic(self, filter_):
        matched = filter_.matches_topics("Learn programming basics")
        assert "python" in matched

    def test_no_topic_match(self, filter_):
        matched = filter_.matches_topics("Cooking recipes")
        assert matched == []


class TestContentFilterShouldIndex:
    def test_index_by_url(self, filter_):
        should, matched = filter_.should_index("https://docs.python.org/3")
        assert should is True
        assert "python" in matched

    def test_index_by_keyword(self, filter_):
        should, matched = filter_.should_index("https://example.com", content="python tutorial")
        assert should is True
        assert "python" in matched

    def test_index_by_title(self, filter_):
        should, matched = filter_.should_index("https://example.com", title="Rust Guide")
        assert should is True
        assert "rust" in matched

    def test_no_match(self, filter_):
        should, matched = filter_.should_index("https://example.com", content="cooking recipes")
        assert should is False
        assert matched == []

    def test_multiple_interests_match(self, filter_):
        should, matched = filter_.should_index(
            "https://example.com",
            content="python and rust comparison"
        )
        assert should is True
        assert "python" in matched
        assert "rust" in matched


class TestContentFilterPages:
    def test_filter_pages_keeps_matching(self, filter_):
        pages = [
            IndexedPage(url="https://example.com/1", content="python tutorial"),
            IndexedPage(url="https://example.com/2", content="cooking recipes"),
            IndexedPage(url="https://example.com/3", content="rust programming"),
        ]
        kept = filter_.filter_pages(pages)
        assert len(kept) == 2
        urls = [p.url for p in kept]
        assert "https://example.com/1" in urls
        assert "https://example.com/3" in urls

    def test_filter_pages_updates_matched_interests(self, filter_):
        page = IndexedPage(url="https://example.com", content="python guide")
        kept = filter_.filter_pages([page])
        assert len(kept) == 1
        assert "python" in kept[0].matched_interests

    def test_filter_pages_empty(self, filter_):
        kept = filter_.filter_pages([])
        assert kept == []


class TestContentFilterHelpers:
    def test_get_all_keywords(self, filter_):
        keywords = filter_.get_all_keywords()
        assert "python" in keywords
        assert "rust" in keywords
        assert "disabled" not in keywords

    def test_get_all_topics(self, filter_):
        topics = filter_.get_all_topics()
        assert "programming" in topics
        assert "systems" in topics

    def test_empty_interests(self):
        f = ContentFilter([])
        should, matched = f.should_index("https://example.com", content="python")
        assert should is False
