"""Tests for content filtering."""

import pytest

from personal_index.config.models import Interest
from personal_index.filter.engine import ContentFilter, FilterResult


@pytest.fixture
def interests():
    return [
        Interest(name="python", keywords=["python", "cpython"], url_patterns=[".*\\.python\\.org.*"], priority=8),
        Interest(name="rust", keywords=["rust", "cargo"], url_patterns=[".*\\.rust-lang\\.org.*"], priority=7),
        Interest(name="disabled", keywords=["disabled"], enabled=False),
    ]


@pytest.fixture
def filter_(interests):
    return ContentFilter(interests)


class TestContentFilterURL:
    def test_matches_url_pattern(self, filter_):
        result = filter_.filter_url("https://docs.python.org/3/library")
        assert result.matched is True
        assert "python" in result.matching_interests

    def test_no_url_match(self, filter_):
        result = filter_.filter_url("https://example.com/page")
        assert result.matched is False

    def test_matches_rust_url(self, filter_):
        result = filter_.filter_url("https://www.rust-lang.org/tools/install")
        assert result.matched is True
        assert "rust" in result.matching_interests

    def test_disabled_interest_not_matched(self, filter_):
        result = filter_.filter_url("https://example.com/disabled")
        assert "disabled" not in result.matching_interests


class TestContentFilterKeywords:
    def test_matches_keyword_in_content(self, filter_):
        result = filter_.filter_content("I love python programming")
        assert result.matched is True
        assert "python" in result.matching_interests

    def test_matches_keyword_in_title(self, filter_):
        result = filter_.filter_content("", title="Rust Programming")
        assert result.matched is True
        assert "rust" in result.matching_interests

    def test_no_keyword_match(self, filter_):
        result = filter_.filter_content("Hello world", title="Welcome")
        assert result.matched is False

    def test_keyword_case_insensitive(self, filter_):
        result = filter_.filter_content("I love PYTHON")
        assert result.matched is True
        assert "python" in result.matching_interests

    def test_disabled_keyword_not_matched(self, filter_):
        result = filter_.filter_content("This is disabled")
        assert "disabled" not in result.matching_interests

    def test_matched_keywords_tracked(self, filter_):
        result = filter_.filter_content("I love python and cpython")
        assert "python" in result.matched_keywords
        assert "cpython" in result.matched_keywords


class TestContentFilterPage:
    def test_filter_page_by_url(self, filter_):
        result = filter_.filter_page("https://docs.python.org/3", "some content")
        assert result.matched is True
        assert "python" in result.matching_interests

    def test_filter_page_by_content(self, filter_):
        result = filter_.filter_page("https://example.com", "python tutorial")
        assert result.matched is True
        assert "python" in result.matching_interests

    def test_filter_page_by_title(self, filter_):
        result = filter_.filter_page("https://example.com", "some text", title="Rust Guide")
        assert result.matched is True
        assert "rust" in result.matching_interests

    def test_filter_page_no_match(self, filter_):
        result = filter_.filter_page("https://example.com", "cooking recipes")
        assert result.matched is False

    def test_filter_page_multiple_matches(self, filter_):
        result = filter_.filter_page("https://example.com", "python and rust comparison")
        assert result.matched is True
        assert "python" in result.matching_interests
        assert "rust" in result.matching_interests

    def test_filter_page_score_accumulates(self, filter_):
        result = filter_.filter_page("https://example.com", "python and rust")
        assert result.score > 0


class TestContentFilterShouldCrawl:
    def test_should_crawl_with_patterns(self, filter_):
        assert filter_.should_crawl("https://docs.python.org/3") is True

    def test_should_crawl_no_patterns(self):
        f = ContentFilter([])
        assert f.should_crawl("https://example.com") is True

    def test_should_not_crawl_unmatched(self, filter_):
        assert filter_.should_crawl("https://random-site.com") is False


class TestContentFilterExtractText:
    def test_extract_short_text(self, filter_):
        text = "Hello world"
        assert filter_.extract_relevant_text(text) == "Hello world"

    def test_extract_truncates_long_text(self, filter_):
        text = "word " * 200
        result = filter_.extract_relevant_text(text, max_length=500)
        assert len(result) <= 500

    def test_extract_truncates_at_word_boundary(self, filter_):
        text = "Hello " * 100
        result = filter_.extract_relevant_text(text, max_length=50)
        assert not result.endswith(" ")


class TestFilterResult:
    def test_default_result(self):
        result = FilterResult()
        assert result.matched is False
        assert result.matching_interests == set()
        assert result.score == 0.0

    def test_result_with_data(self):
        result = FilterResult(matched=True, matching_interests={"python"}, score=5.0)
        assert result.matched is True
        assert "python" in result.matching_interests
        assert result.score == 5.0


class TestEmptyFilter:
    def test_empty_interests_no_match(self):
        f = ContentFilter([])
        result = f.filter_page("https://example.com", "python")
        assert result.matched is False

    def test_empty_interests_should_crawl(self):
        f = ContentFilter([])
        assert f.should_crawl("https://example.com") is True
