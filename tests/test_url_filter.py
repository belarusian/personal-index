"""Tests for URL filtering module."""

from __future__ import annotations

import pytest

from personal_index.url_filter import UrlFilter, UrlFilterRule


class TestUrlFilterRule:
    """Tests for UrlFilterRule class."""

    def test_exact_match(self):
        rule = UrlFilterRule("http://example.com")
        assert rule.matches("http://example.com")
        assert not rule.matches("http://example.com/page")

    def test_fnmatch_wildcard(self):
        rule = UrlFilterRule("http://example.com/*")
        assert rule.matches("http://example.com/page")
        assert rule.matches("http://example.com/deep/path")
        assert not rule.matches("http://other.com/page")

    def test_regex_pattern(self):
        rule = UrlFilterRule("re:http://example\\.com/\\d+")
        assert rule.matches("http://example.com/123")
        assert not rule.matches("http://example.com/abc")

    def test_invalid_regex(self):
        rule = UrlFilterRule("re:[invalid")
        assert not rule.matches("anything")

    def test_description_preserved(self):
        rule = UrlFilterRule("http://spam.com", description="Spam site")
        assert rule.description == "Spam site"


class TestUrlFilter:
    """Tests for UrlFilter class."""

    def setup_method(self):
        self.filter = UrlFilter()

    def test_default_allows_all(self):
        assert self.filter.is_allowed("http://example.com")
        assert self.filter.is_allowed("http://any-url.com")

    def test_blacklist_blocks_exact(self):
        self.filter.add_blacklist("http://spam.com")
        assert self.filter.is_blocked("http://spam.com")
        assert self.filter.is_allowed("http://example.com")

    def test_blacklist_blocks_wildcard(self):
        self.filter.add_blacklist("http://spam.com/*")
        assert self.filter.is_blocked("http://spam.com/page")
        assert self.filter.is_blocked("http://spam.com/deep/path")
        assert self.filter.is_allowed("http://example.com")

    def test_whitelist_overrides_blacklist(self):
        self.filter.add_blacklist("http://example.com/*")
        self.filter.add_whitelist("http://example.com/allowed")
        assert self.filter.is_blocked("http://example.com/blocked")
        assert self.filter.is_allowed("http://example.com/allowed")

    def test_filter_urls(self):
        self.filter.add_blacklist("http://spam.com")
        urls = ["http://good.com", "http://spam.com", "http://also-good.com"]
        result = self.filter.filter_urls(urls)
        assert result == ["http://good.com", "http://also-good.com"]

    def test_get_blocked_urls(self):
        self.filter.add_blacklist("http://spam.com")
        urls = ["http://good.com", "http://spam.com", "http://also-good.com"]
        result = self.filter.get_blocked_urls(urls)
        assert result == ["http://spam.com"]

    def test_get_matching_rule(self):
        self.filter.add_blacklist("http://spam.com", description="Spam")
        rule = self.filter.get_matching_rule("http://spam.com")
        assert rule is not None
        assert rule.description == "Spam"

    def test_get_matching_rule_none(self):
        rule = self.filter.get_matching_rule("http://example.com")
        assert rule is None

    def test_regex_blacklist(self):
        self.filter.add_blacklist("re:.*\\.pdf$")
        assert self.filter.is_blocked("http://example.com/doc.pdf")
        assert self.filter.is_allowed("http://example.com/page.html")

    def test_clear(self):
        self.filter.add_blacklist("http://spam.com")
        self.filter.add_whitelist("http://good.com")
        self.filter.clear()
        assert self.filter.blacklist_count == 0
        assert self.filter.whitelist_count == 0
        assert self.filter.is_allowed("http://spam.com")

    def test_clear_blacklist(self):
        self.filter.add_blacklist("http://spam.com")
        self.filter.add_whitelist("http://good.com")
        self.filter.clear_blacklist()
        assert self.filter.blacklist_count == 0
        assert self.filter.whitelist_count == 1

    def test_clear_whitelist(self):
        self.filter.add_blacklist("http://spam.com")
        self.filter.add_whitelist("http://good.com")
        self.filter.clear_whitelist()
        assert self.filter.blacklist_count == 1
        assert self.filter.whitelist_count == 0

    def test_multiple_blacklist_rules(self):
        self.filter.add_blacklist("http://spam.com")
        self.filter.add_blacklist("http://ads.com")
        assert self.filter.is_blocked("http://spam.com")
        assert self.filter.is_blocked("http://ads.com")
        assert self.filter.is_allowed("http://example.com")

    def test_empty_filter(self):
        assert self.filter.filter_urls([]) == []
        assert self.filter.get_blocked_urls([]) == []

    def test_counts(self):
        self.filter.add_blacklist("http://a.com")
        self.filter.add_blacklist("http://b.com")
        self.filter.add_whitelist("http://c.com")
        assert self.filter.blacklist_count == 2
        assert self.filter.whitelist_count == 1
