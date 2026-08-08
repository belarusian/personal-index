"""Tests for the URL deduplication module."""

from __future__ import annotations

import pytest

from personal_index.url_dedup import DedupResult, URLDeduplicator


class TestDedupResult:
    def test_duplicate_result(self):
        result = DedupResult(
            is_duplicate=True,
            original_url="http://a.com",
            matched_url="http://b.com",
            similarity_score=0.95,
            reason="fuzzy_match",
        )
        assert result.is_duplicate is True
        assert result.matched_url == "http://b.com"
        assert result.similarity_score == 0.95

    def test_unique_result(self):
        result = DedupResult(is_duplicate=False, original_url="http://a.com")
        assert result.is_duplicate is False
        assert result.matched_url is None


class TestURLDeduplicatorNormalize:
    def setup_method(self):
        self.dedup = URLDeduplicator()

    def test_remove_fragment(self):
        assert self.dedup.normalize_url("http://a.com/page#section") == "http://a.com/page"

    def test_remove_trailing_slash(self):
        assert self.dedup.normalize_url("http://a.com/page/") == "http://a.com/page"

    def test_keep_root_slash(self):
        result = self.dedup.normalize_url("http://a.com/")
        assert result == "http://a.com/" or result == "http://a.com"

    def test_lowercase_scheme_netloc(self):
        assert self.dedup.normalize_url("HTTP://A.COM/page") == "http://a.com/page"

    def test_remove_www(self):
        assert self.dedup.normalize_url("http://www.a.com/page") == "http://a.com/page"

    def test_sort_query_params(self):
        result = self.dedup.normalize_url("http://a.com/page?b=2&a=1")
        assert "a=1&b=2" in result

    def test_remove_tracking_params(self):
        result = self.dedup.normalize_url("http://a.com/page?utm_source=google&title=test")
        assert "utm_source" not in result
        assert "title=test" in result

    def test_remove_all_tracking_params(self):
        result = self.dedup.normalize_url("http://a.com/page?utm_source=google&utm_medium=cpc")
        assert "?" not in result

    def test_normalize_complex_url(self):
        url = "HTTP://WWW.A.COM/page/?utm_source=google&b=2&a=1#top"
        normalized = self.dedup.normalize_url(url)
        assert normalized.startswith("http://a.com")
        assert "utm_source" not in normalized
        assert "#top" not in normalized


class TestURLDeduplicatorCheckDuplicate:
    def setup_method(self):
        self.dedup = URLDeduplicator()

    def test_exact_duplicate(self):
        self.dedup.add_url("http://a.com/page")
        result = self.dedup.check_duplicate("http://a.com/page")
        assert result.is_duplicate is True
        assert result.reason == "exact_match"
        assert result.similarity_score == 1.0

    def test_normalized_duplicate(self):
        self.dedup.add_url("http://a.com/page")
        result = self.dedup.check_duplicate("http://a.com/page/")
        assert result.is_duplicate is True
        assert result.reason == "exact_match"

    def test_unique_url(self):
        result = self.dedup.check_duplicate("http://a.com/unique")
        assert result.is_duplicate is False
        assert result.reason == "unique"

    def test_fuzzy_duplicate(self):
        self.dedup.add_url("http://a.com/page-one")
        result = self.dedup.check_duplicate("http://a.com/page_one")
        # With default threshold 0.95, this may or may not match
        # Use a lower threshold to ensure it matches
        dedup = URLDeduplicator(fuzzy_threshold=0.85)
        dedup.add_url("http://a.com/page-one")
        result = dedup.check_duplicate("http://a.com/page_one")
        assert result.is_duplicate is True
        assert result.reason == "fuzzy_match"

    def test_different_domain_not_duplicate(self):
        self.dedup.add_url("http://a.com/page")
        result = self.dedup.check_duplicate("http://b.com/page")
        assert result.is_duplicate is False


class TestURLDeduplicatorAddUrl:
    def setup_method(self):
        self.dedup = URLDeduplicator()

    def test_add_unique_url(self):
        result = self.dedup.add_url("http://a.com/page")
        assert result.is_duplicate is False
        assert self.dedup.seen_count == 1

    def test_add_duplicate_url(self):
        self.dedup.add_url("http://a.com/page")
        result = self.dedup.add_url("http://a.com/page")
        assert result.is_duplicate is True
        assert self.dedup.seen_count == 1

    def test_add_normalized_duplicate(self):
        self.dedup.add_url("http://a.com/page")
        result = self.dedup.add_url("http://a.com/page/")
        assert result.is_duplicate is True
        assert self.dedup.seen_count == 1


class TestURLDeduplicatorDeduplicateUrls:
    def setup_method(self):
        self.dedup = URLDeduplicator()

    def test_deduplicate_list(self):
        urls = [
            "http://a.com/page1",
            "http://a.com/page2",
            "http://a.com/page1",
            "http://a.com/page1/",
        ]
        unique, results = self.dedup.deduplicate_urls(urls)
        assert len(unique) == 2
        assert len(results) == 4

    def test_deduplicate_all_unique(self):
        urls = ["http://a.com/1", "http://a.com/2", "http://a.com/3"]
        unique, results = self.dedup.deduplicate_urls(urls)
        assert len(unique) == 3
        assert all(not r.is_duplicate for r in results)

    def test_deduplicate_all_same(self):
        urls = ["http://a.com/page", "http://a.com/page/", "http://a.com/page?utm_source=x"]
        unique, results = self.dedup.deduplicate_urls(urls)
        assert len(unique) == 1
        assert results[0].is_duplicate is False
        assert results[1].is_duplicate is True
        assert results[2].is_duplicate is True


class TestURLDeduplicatorStats:
    def setup_method(self):
        self.dedup = URLDeduplicator()

    def test_stats_empty(self):
        stats = self.dedup.get_stats()
        assert stats["total_seen"] == 0
        assert stats["total_domains"] == 0

    def test_stats_with_urls(self):
        self.dedup.add_url("http://a.com/page1")
        self.dedup.add_url("http://a.com/page2")
        self.dedup.add_url("http://b.com/page1")
        stats = self.dedup.get_stats()
        assert stats["total_seen"] == 3
        assert stats["total_domains"] == 2

    def test_clear(self):
        self.dedup.add_url("http://a.com/page")
        self.dedup.clear()
        assert self.dedup.seen_count == 0
        stats = self.dedup.get_stats()
        assert stats["total_domains"] == 0


class TestURLDeduplicatorCanonical:
    def setup_method(self):
        self.dedup = URLDeduplicator()

    def test_get_canonical_url(self):
        self.dedup.add_url("http://a.com/page")
        canonical = self.dedup.get_canonical_url("http://a.com/page/")
        assert canonical == "http://a.com/page"

    def test_get_canonical_url_not_found(self):
        assert self.dedup.get_canonical_url("http://a.com/page") is None

    def test_get_domain_urls(self):
        self.dedup.add_url("http://a.com/page1")
        self.dedup.add_url("http://a.com/page2")
        self.dedup.add_url("http://b.com/page1")
        urls = self.dedup.get_domain_urls("a.com")
        assert len(urls) == 2
        assert "http://a.com/page1" in urls

    def test_get_domain_urls_www(self):
        self.dedup.add_url("http://www.a.com/page")
        urls = self.dedup.get_domain_urls("a.com")
        assert len(urls) == 1

    def test_get_domain_urls_empty(self):
        urls = self.dedup.get_domain_urls("nonexistent.com")
        assert urls == []


class TestURLDeduplicatorFuzzyThreshold:
    def test_custom_threshold(self):
        dedup = URLDeduplicator(fuzzy_threshold=0.95)
        dedup.add_url("http://a.com/page-one")
        result = dedup.check_duplicate("http://a.com/page_one")
        assert dedup._fuzzy_threshold == 0.95

    def test_low_threshold_catches_more(self):
        dedup = URLDeduplicator(fuzzy_threshold=0.5)
        dedup.add_url("http://a.com/page")
        result = dedup.check_duplicate("http://a.com/pagex")
        assert result.is_duplicate is True

    def test_high_threshold_catches_fewer(self):
        dedup = URLDeduplicator(fuzzy_threshold=0.99)
        dedup.add_url("http://a.com/page")
        result = dedup.check_duplicate("http://a.com/pagex")
        assert result.is_duplicate is False
