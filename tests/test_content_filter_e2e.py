"""End-to-end tests for content filtering."""

from __future__ import annotations

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.models import CrawledPage


class TestContentFilterE2E:
    """Test content filtering with realistic scenarios."""

    def test_filter_includes_long_content(self):
        """Content above minimum length passes filter."""
        config = FilterConfig(min_content_length=100, require_interest_match=False)
        filter_engine = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com/long",
            title="Long Content",
            content="This is a page with enough content to pass the minimum length filter. "
                    "It has more than one hundred words of meaningful content that should "
                    "definitely pass through the content filter without any issues at all.",
        )
        assert filter_engine.should_include(page)

    def test_filter_excludes_short_content(self):
        """Content below minimum length is filtered out."""
        config = FilterConfig(min_content_length=100, require_interest_match=False)
        filter_engine = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com/short",
            title="Short Content",
            content="Too short.",
        )
        assert not filter_engine.should_include(page)

    def test_filter_excludes_empty_content(self):
        """Empty content is always filtered out."""
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com/empty",
            title="Empty Page",
            content="",
        )
        assert not filter_engine.should_include(page)

    def test_filter_with_low_min_length(self):
        """Filter with low minimum length passes short content."""
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com/default",
            title="Default Filter",
            content="This content should pass the default filter settings.",
        )
        assert filter_engine.should_include(page)

    def test_filter_blocked_domains(self):
        """Filter can exclude by blocked domains."""
        config = FilterConfig(
            blocked_domains=["spam.com"],
            min_content_length=10,
            require_interest_match=False,
        )
        filter_engine = ContentFilter(config=config)
        spam_page = CrawledPage(
            url="https://spam.com/page",
            title="Spam Page",
            content="This is spam content that should be filtered out because the domain is blocked.",
        )
        assert not filter_engine.should_include(spam_page)

        good_page = CrawledPage(
            url="https://example.com/page",
            title="Good Page",
            content="This is good content from a non-blocked domain that should pass the filter correctly.",
        )
        assert filter_engine.should_include(good_page)

    def test_filter_blocked_patterns(self):
        """Filter can exclude by content patterns."""
        config = FilterConfig(
            blocked_patterns=["\\bspam\\b"],
            min_content_length=10,
            require_interest_match=False,
        )
        filter_engine = ContentFilter(config=config)
        spam_page = CrawledPage(
            url="https://example.com/spam",
            title="Spam Page",
            content="This content contains spam keywords that should be filtered out.",
        )
        assert not filter_engine.should_include(spam_page)

    def test_filter_required_patterns(self):
        """Filter requires content to match certain patterns."""
        config = FilterConfig(
            required_patterns=["\\bpython\\b"],
            min_content_length=10,
            require_interest_match=False,
        )
        filter_engine = ContentFilter(config=config)
        matching_page = CrawledPage(
            url="https://example.com/python",
            title="Python Page",
            content="This page is about Python programming and should match the required pattern.",
        )
        assert filter_engine.should_include(matching_page)

        non_matching = CrawledPage(
            url="https://example.com/rust",
            title="Rust Page",
            content="This page is about Rust systems programming and memory safety.",
        )
        assert not filter_engine.should_include(non_matching)

    def test_filter_reasons(self):
        """Filter provides reasons for exclusion."""
        config = FilterConfig(min_content_length=100, require_interest_match=False)
        filter_engine = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com/short",
            title="X",
            content="Short.",
        )
        reasons = filter_engine.get_filter_reasons(page)
        assert len(reasons) > 0
        assert any("content length" in r for r in reasons)
        assert any("title too short" in r for r in reasons)

    def test_filter_pages_batch(self):
        """Filter a batch of pages."""
        config = FilterConfig(min_content_length=50, require_interest_match=False)
        filter_engine = ContentFilter(config=config)
        pages = [
            CrawledPage(url="https://example.com/1", title="Good",
                        content="This is a good page with enough content to pass the filter."),
            CrawledPage(url="https://example.com/2", title="Bad",
                        content="Short."),
        ]
        filtered = filter_engine.filter_pages(pages)
        assert len(filtered) == 1
        assert filtered[0].url == "https://example.com/1"
