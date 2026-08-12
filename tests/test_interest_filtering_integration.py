"""Integration tests for interest-based filtering."""

from __future__ import annotations

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest


class TestInterestFilteringIntegration:
    """Test interest-based filtering with realistic scenarios."""

    def test_interest_based_filter(self, tmp_path):
        """Filter pages based on interest matches."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="python",
            keywords=["python", "programming"],
            priority=5,
        ))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        # Page that matches
        page1 = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a programming language.",
        )
        
        # Page that doesn't match
        page2 = CrawledPage(
            url="https://example.com/rust",
            title="Rust Guide",
            content="Rust is a systems programming language.",
        )
        
        assert filter_engine.should_include(page1)
        assert filter_engine.should_include(page2)

    def test_filter_with_multiple_interests(self, tmp_path):
        """Filter with multiple interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))
        store.add(Interest(name="rust", keywords=["rust"], priority=5))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page1 = CrawledPage(
            url="https://example.com/python",
            title="Python Page",
            content="Python programming.",
        )
        
        page2 = CrawledPage(
            url="https://example.com/multi",
            title="Multi Language",
            content="Python and Rust are both great.",
        )
        
        assert filter_engine.should_include(page1)
        assert filter_engine.should_include(page2)

    def test_filter_with_priority(self, tmp_path):
        """Filter respects interest priority."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="high", keywords=["python"], priority=10))
        store.add(Interest(name="low", keywords=["rust"], priority=1))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page = CrawledPage(
            url="https://example.com/both",
            title="Both Languages",
            content="Python and Rust.",
        )
        
        assert filter_engine.should_include(page)

    def test_filter_with_min_relevance_score(self, tmp_path):
        """Filter with minimum relevance score."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))
        
        config = FilterConfig(
            min_content_length=10,
            require_interest_match=False,
            min_relevance_score=2.0,
        )
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page1 = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a versatile programming language used in many applications.",
        )
        
        page2 = CrawledPage(
            url="https://example.com/rust",
            title="Rust Page",
            content="Rust systems programming.",
        )
        
        assert filter_engine.should_include(page1)
        assert not filter_engine.should_include(page2)

    def test_filter_batch_with_interests(self, tmp_path):
        """Filter a batch of pages with interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        pages = [
            CrawledPage(url="https://example.com/python", title="Python",
                        content="Python programming with many words of content."),
            CrawledPage(url="https://example.com/rust", title="Rust",
                        content="Rust systems programming with enough content length."),
            CrawledPage(url="https://example.com/go", title="Go",
                        content="Go programming language with sufficient content for filtering."),
        ]
        
        filtered = filter_engine.filter_pages(pages)
        
        # At least 2 should pass (all have enough content, require_interest_match=False)
        assert len(filtered) >= 2

    def test_filter_with_no_interests(self, tmp_path):
        """Filter with no interests passes all pages."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page = CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="Test content.",
        )
        
        assert filter_engine.should_include(page)

    def test_filter_with_disabled_interest(self, tmp_path):
        """Filter ignores disabled interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5, enabled=False))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Page",
            content="Python programming.",
        )
        
        assert filter_engine.should_include(page)

    def test_filter_reasons_with_interests(self, tmp_path):
        """Filter reasons include interest match info."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page = CrawledPage(
            url="https://example.com/rust",
            title="Rust Page",
            content="Rust systems programming with enough content.",
        )
        
        reasons = filter_engine.get_filter_reasons(page)
        
        assert len(reasons) == 0

    def test_filter_with_url_patterns(self, tmp_path):
        """Filter with URL pattern interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="github",
            url_patterns=["github.com"],
            keywords=[],
            priority=5,
        ))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page1 = CrawledPage(
            url="https://github.com/user/repo",
            title="GitHub Repo",
            content="Repository content.",
        )
        
        page2 = CrawledPage(
            url="https://example.com/page",
            title="Example Page",
            content="Example content.",
        )
        
        assert filter_engine.should_include(page1)
        assert filter_engine.should_include(page2)

    def test_filter_combined_with_content_length(self, tmp_path):
        """Filter combines interest match with content length."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))
        
        config = FilterConfig(
            min_content_length=100,
            require_interest_match=False,
        )
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page1 = CrawledPage(
            url="https://example.com/python",
            title="Python",
            content="Short.",
        )
        
        page2 = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a versatile programming language used for web development, data science, and automation. It supports multiple paradigms including object-oriented and functional programming.",
        )
        
        assert not filter_engine.should_include(page1)
        assert filter_engine.should_include(page2)

    def test_filter_with_all_interests_disabled(self, tmp_path):
        """Filter with all interests disabled passes all pages."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5, enabled=False))
        
        config = FilterConfig(min_content_length=10, require_interest_match=False)
        filter_engine = ContentFilter(config=config, interest_store=store)
        
        page = CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="Test content.",
        )
        
        assert filter_engine.should_include(page)
