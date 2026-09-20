"""Adversarial tests for personal_index.stats module.

Contracts tested:
- get_index_stats() with falsy search_index returns all-default IndexStats
- get_index_stats() with empty index returns correct defaults
- total_pages, total_words, unique_domains, avg_content_length computed correctly
- pages_with_interests counts interest matches (one per matched interest, not per page)
- top_domains and top_interests capped to top 10
- oldest_page and newest_page set only when at least one page has crawled_at
- format_index_stats() output format
"""

import tempfile
from datetime import datetime, timezone

from personal_index.stats import StatsCollector
from personal_index.search_index import SearchIndex
from personal_index.models import CrawledPage


def make_collector(pages=None):
    """Create a StatsCollector with optional pages."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        index_path = f.name
    index = SearchIndex(index_path=index_path)
    if pages:
        for url, page in pages.items():
            index.add(page)
    return StatsCollector(search_index=index)


class TestFalsySearchIndex:
    """get_index_stats() with falsy search_index returns all-default IndexStats."""

    def test_none_search_index(self):
        collector = StatsCollector(search_index=None)
        stats = collector.get_index_stats()
        assert stats.total_pages == 0
        assert stats.total_words == 0
        assert stats.unique_domains == 0
        assert stats.avg_content_length == 0.0
        assert stats.pages_with_interests == 0
        assert stats.top_domains == []
        assert stats.top_interests == []
        assert stats.oldest_page is None
        assert stats.newest_page is None

    def test_default_search_index(self):
        collector = StatsCollector()
        stats = collector.get_index_stats()
        assert stats.total_pages == 0


class TestEmptyIndex:
    """get_index_stats() with empty index returns correct defaults."""

    def test_empty_index(self):
        collector = make_collector()
        stats = collector.get_index_stats()
        assert stats.total_pages == 0
        assert stats.total_words == 0
        assert stats.unique_domains == 0
        assert stats.avg_content_length == 0.0
        assert stats.pages_with_interests == 0
        assert stats.top_domains == []
        assert stats.top_interests == []
        assert stats.oldest_page is None
        assert stats.newest_page is None


class TestBasicStats:
    """total_pages, total_words, unique_domains, avg_content_length."""

    def test_single_page(self):
        page = CrawledPage(url="http://example.com", content="hello world foo bar")
        collector = make_collector({"http://example.com": page})
        stats = collector.get_index_stats()
        assert stats.total_pages == 1
        assert stats.total_words == 4
        assert stats.unique_domains == 1
        assert stats.avg_content_length == 19.0

    def test_multiple_pages_same_domain(self):
        p1 = CrawledPage(url="http://example.com/a", content="one two")
        p2 = CrawledPage(url="http://example.com/b", content="three four five")
        collector = make_collector({
            "http://example.com/a": p1,
            "http://example.com/b": p2,
        })
        stats = collector.get_index_stats()
        assert stats.total_pages == 2
        assert stats.total_words == 5
        assert stats.unique_domains == 1
        assert stats.avg_content_length == 11.0

    def test_multiple_domains(self):
        p1 = CrawledPage(url="http://example.com/a", content="one")
        p2 = CrawledPage(url="http://other.com/b", content="two")
        collector = make_collector({
            "http://example.com/a": p1,
            "http://other.com/b": p2,
        })
        stats = collector.get_index_stats()
        assert stats.total_pages == 2
        assert stats.unique_domains == 2

    def test_empty_content(self):
        page = CrawledPage(url="http://example.com", content="")
        collector = make_collector({"http://example.com": page})
        stats = collector.get_index_stats()
        assert stats.total_pages == 1
        assert stats.total_words == 0
        assert stats.avg_content_length == 0.0

    def test_whitespace_content(self):
        page = CrawledPage(url="http://example.com", content="   ")
        collector = make_collector({"http://example.com": page})
        stats = collector.get_index_stats()
        assert stats.total_pages == 1
        assert stats.total_words == 0
        assert stats.avg_content_length == 3.0

    def test_unicode_content(self):
        page = CrawledPage(url="http://example.com", content="héllo wörld")
        collector = make_collector({"http://example.com": page})
        stats = collector.get_index_stats()
        assert stats.total_pages == 1
        assert stats.total_words == 2


class TestInterestStats:
    """pages_with_interests counts interest matches (one per matched interest, not per page)."""

    def test_no_interests(self):
        page = CrawledPage(url="http://example.com", content="hello")
        collector = make_collector({"http://example.com": page})
        stats = collector.get_index_stats()
        assert stats.pages_with_interests == 0
        assert stats.top_interests == []

    def test_single_interest_single_page(self):
        page = CrawledPage(url="http://example.com", content="hello", matched_interests=["tech"])
        collector = make_collector({"http://example.com": page})
        stats = collector.get_index_stats()
        assert stats.pages_with_interests == 1
        assert stats.top_interests == [("tech", 1)]

    def test_multiple_interests_single_page(self):
        page = CrawledPage(url="http://example.com", content="hello", matched_interests=["tech", "science"])
        collector = make_collector({"http://example.com": page})
        stats = collector.get_index_stats()
        # One per matched interest, not one per page
        assert stats.pages_with_interests == 2
        assert len(stats.top_interests) == 2

    def test_same_interest_multiple_pages(self):
        p1 = CrawledPage(url="http://example.com/a", content="hello", matched_interests=["tech"])
        p2 = CrawledPage(url="http://example.com/b", content="world", matched_interests=["tech"])
        collector = make_collector({
            "http://example.com/a": p1,
            "http://example.com/b": p2,
        })
        stats = collector.get_index_stats()
        assert stats.pages_with_interests == 2
        assert stats.top_interests == [("tech", 2)]

    def test_top_interests_capped_at_10(self):
        pages = {}
        for i in range(15):
            url = f"http://example.com/{i}"
            page = CrawledPage(url=url, content="hello", matched_interests=[f"interest_{i}"])
            pages[url] = page
        collector = make_collector(pages)
        stats = collector.get_index_stats()
        assert len(stats.top_interests) == 10
        assert stats.pages_with_interests == 15


class TestDomainStats:
    """top_domains capped to top 10, sorted by count descending."""

    def test_top_domains_capped_at_10(self):
        pages = {}
        for i in range(15):
            url = f"http://domain{i}.com/page"
            page = CrawledPage(url=url, content="hello")
            pages[url] = page
        collector = make_collector(pages)
        stats = collector.get_index_stats()
        assert len(stats.top_domains) == 10

    def test_top_domains_sorted_by_count(self):
        pages = {}
        # domain1.com gets 3 pages
        for i in range(3):
            url = f"http://domain1.com/page{i}"
            pages[url] = CrawledPage(url=url, content="hello")
        # domain2.com gets 2 pages
        for i in range(2):
            url = f"http://domain2.com/page{i}"
            pages[url] = CrawledPage(url=url, content="hello")
        collector = make_collector(pages)
        stats = collector.get_index_stats()
        assert stats.top_domains[0][0] == "domain1.com"
        assert stats.top_domains[0][1] == 3
        assert stats.top_domains[1][0] == "domain2.com"
        assert stats.top_domains[1][1] == 2


class TestTimestampStats:
    """oldest_page and newest_page set only when at least one page has crawled_at."""

    def test_single_timestamp(self):
        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        page = CrawledPage(url="http://example.com", content="hello", crawled_at=ts)
        collector = make_collector({"http://example.com": page})
        stats = collector.get_index_stats()
        assert stats.oldest_page == ts
        assert stats.newest_page == ts

    def test_multiple_timestamps(self):
        ts1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        p1 = CrawledPage(url="http://example.com/a", content="hello", crawled_at=ts1)
        p2 = CrawledPage(url="http://example.com/b", content="world", crawled_at=ts2)
        collector = make_collector({
            "http://example.com/a": p1,
            "http://example.com/b": p2,
        })
        stats = collector.get_index_stats()
        assert stats.oldest_page == ts1
        assert stats.newest_page == ts2


class TestFormatIndexStats:
    """format_index_stats() output format."""

    def test_empty_index_format(self):
        collector = make_collector()
        output = collector.format_index_stats()
        assert "=== Index Statistics ===" in output
        assert "Total pages: 0" in output
        assert "Total words: 0" in output
        assert "Unique domains: 0" in output
        assert "Avg content length: 0" in output
        assert "Interest matches: 0" in output

    def test_with_data_format(self):
        page = CrawledPage(url="http://example.com", content="hello world", matched_interests=["tech"])
        collector = make_collector({"http://example.com": page})
        output = collector.format_index_stats()
        assert "Total pages: 1" in output
        assert "Total words: 2" in output
        assert "Unique domains: 1" in output
        assert "Interest matches: 1" in output
        assert "Top domains:" in output
        assert "example.com: 1" in output
        assert "Top interests:" in output
        assert "tech: 1" in output
