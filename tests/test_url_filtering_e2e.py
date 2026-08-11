"""End-to-end tests for URL filtering."""

from __future__ import annotations

import pytest

from personal_index.url_filter import UrlFilter


class TestURLFilteringE2E:
    """Test URL filtering with realistic scenarios."""

    def test_filter_by_extension(self):
        """Filter URLs by file extension."""
        filter_engine = UrlFilter()
        filter_engine.add_blacklist("*.css")
        filter_engine.add_blacklist("*.js")
        filter_engine.add_blacklist("*.png")
        
        assert not filter_engine.is_allowed("https://example.com/style.css")
        assert not filter_engine.is_allowed("https://example.com/script.js")
        assert not filter_engine.is_allowed("https://example.com/image.png")
        assert filter_engine.is_allowed("https://example.com/page.html")
        assert filter_engine.is_allowed("https://example.com/article")

    def test_filter_by_pattern(self):
        """Filter URLs by regex pattern."""
        filter_engine = UrlFilter()
        filter_engine.add_blacklist("re:.*\\?.*tracking=.*")
        filter_engine.add_blacklist("re:.*\\/admin\\/.*")
        
        assert not filter_engine.is_allowed("https://example.com/page?tracking=123")
        assert not filter_engine.is_allowed("https://example.com/admin/users")
        assert filter_engine.is_allowed("https://example.com/page")
        assert filter_engine.is_allowed("https://example.com/user/profile")

    def test_filter_whitelist_precedence(self):
        """Whitelist takes precedence over blacklist."""
        filter_engine = UrlFilter()
        filter_engine.add_blacklist("re:.*spam.*")
        filter_engine.add_whitelist("re:.*allowed.*")
        
        assert not filter_engine.is_allowed("https://example.com/spam")
        assert filter_engine.is_allowed("https://example.com/allowed")

    def test_filter_empty_config(self):
        """Filter with empty config passes all URLs."""
        filter_engine = UrlFilter()
        assert filter_engine.is_allowed("https://example.com/page")
        assert filter_engine.is_allowed("https://spam.com/page")

    def test_filter_with_description(self):
        """Filter rules can have descriptions."""
        filter_engine = UrlFilter()
        filter_engine.add_blacklist("*.pdf", description="PDF documents")
        
        assert not filter_engine.is_allowed("https://example.com/doc.pdf")

    def test_filter_multiple_rules(self):
        """Filter with multiple rules."""
        filter_engine = UrlFilter()
        filter_engine.add_blacklist("*.pdf")
        filter_engine.add_blacklist("*.doc")
        filter_engine.add_blacklist("*.jpg")
        
        assert not filter_engine.is_allowed("https://example.com/doc.pdf")
        assert not filter_engine.is_allowed("https://example.com/report.doc")
        assert not filter_engine.is_allowed("https://example.com/image.jpg")
        assert filter_engine.is_allowed("https://example.com/page.html")

    def test_filter_exact_match(self):
        """Filter can match exact URLs."""
        filter_engine = UrlFilter()
        filter_engine.add_blacklist("https://example.com/blocked")
        
        assert not filter_engine.is_allowed("https://example.com/blocked")
        assert filter_engine.is_allowed("https://example.com/other")

    def test_filter_regex_match(self):
        """Filter supports regex patterns."""
        filter_engine = UrlFilter()
        filter_engine.add_blacklist("re:.*\\.(pdf|doc)$")
        
        assert not filter_engine.is_allowed("https://example.com/doc.pdf")
        assert not filter_engine.is_allowed("https://example.com/report.doc")
        assert filter_engine.is_allowed("https://example.com/page.html")

    def test_filter_is_blocked(self):
        """Test is_blocked method."""
        filter_engine = UrlFilter()
        filter_engine.add_blacklist("*.pdf")
        
        assert filter_engine.is_blocked("https://example.com/doc.pdf")
        assert not filter_engine.is_blocked("https://example.com/page.html")
