"""Tests for personal_index.stats."""

from datetime import datetime, timezone

import pytest

from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest, InterestType
from personal_index.search_index import SearchIndex
from personal_index.stats import CrawlStats, IndexStats, StatsCollector


@pytest.fixture
def interest_store(tmp_path):
    store = InterestStore(store_path=str(tmp_path / "interests.json"))
    store.add(Interest("Py", InterestType.KEYWORD, "python", 5))
    return store


@pytest.fixture
def search_index(tmp_path):
    return SearchIndex(index_path=str(tmp_path / "index.json"))


@pytest.fixture
def collector(interest_store, search_index):
    return StatsCollector(
        interest_store=interest_store,
        search_index=search_index,
    )


class TestIndexStats:
    """Tests for IndexStats."""

    def test_defaults(self):
        stats = IndexStats()
        assert stats.total_pages == 0
        assert stats.total_words == 0
        assert stats.unique_domains == 0
        assert stats.avg_content_length == 0.0


class TestCrawlStats:
    """Tests for CrawlStats."""

    def test_defaults(self):
        stats = CrawlStats()
        assert stats.total_crawls == 0
        assert stats.total_pages_crawled == 0
        assert stats.total_errors == 0


class TestStatsCollector:
    """Tests for StatsCollector."""

    def test_empty_index(self, collector):
        stats = collector.get_index_stats()
        assert stats.total_pages == 0
        assert stats.total_words == 0

    def test_index_with_pages(self, collector):
        collector.search_index.add(CrawledPage(
            url="https://example.com/page1",
            title="Python Guide",
            content="Python is a great programming language",
            matched_interests=["Py"],
        ))
        collector.search_index.add(CrawledPage(
            url="https://example.com/page2",
            title="Another Page",
            content="More content here",
        ))

        stats = collector.get_index_stats()
        assert stats.total_pages == 2
        assert stats.total_words > 0
        assert stats.unique_domains == 1
        assert stats.pages_with_interests == 1

    def test_pages_with_interests_counts_matches_not_pages(self, collector):
        """Pin corrected claim: value counts interest matches, not distinct pages."""
        collector.search_index.add(CrawledPage(
            url="https://example.com/page1",
            title="Multi Interest",
            content="Some content here",
            matched_interests=["Py", "Go", "Rust"],
        ))
        stats = collector.get_index_stats()
        assert stats.total_pages == 1
        assert stats.pages_with_interests == 3
        assert "Interest matches: 3" in collector.format_index_stats()

    def test_top_domains(self, collector):
        collector.search_index.add(CrawledPage(
            url="https://a.com/page1",
            title="Page 1",
            content="Content 1",
        ))
        collector.search_index.add(CrawledPage(
            url="https://a.com/page2",
            title="Page 2",
            content="Content 2",
        ))
        collector.search_index.add(CrawledPage(
            url="https://b.com/page1",
            title="Page 3",
            content="Content 3",
        ))

        stats = collector.get_index_stats()
        domain_counts = dict(stats.top_domains)
        assert domain_counts.get("a.com", 0) == 2
        assert domain_counts.get("b.com", 0) == 1

    def test_top_interests(self, collector):
        collector.search_index.add(CrawledPage(
            url="https://a.com",
            title="Python",
            content="Python stuff",
            matched_interests=["Py"],
        ))
        collector.search_index.add(CrawledPage(
            url="https://b.com",
            title="Python Again",
            content="More python",
            matched_interests=["Py"],
        ))

        stats = collector.get_index_stats()
        interest_counts = dict(stats.top_interests)
        assert interest_counts.get("Py", 0) == 2

    def test_format_index_stats(self, collector):
        output = collector.format_index_stats()
        assert "=== Index Statistics ===" in output
        assert "Total pages: 0" in output

    def test_format_with_data(self, collector):
        collector.search_index.add(CrawledPage(
            url="https://example.com",
            title="Test",
            content="Some test content",
            matched_interests=["Py"],
        ))
        output = collector.format_index_stats()
        assert "Total pages: 1" in output
        assert "Top domains:" in output

    def test_no_search_index(self, interest_store):
        collector = StatsCollector(interest_store=interest_store)
        stats = collector.get_index_stats()
        assert stats.total_pages == 0

    def test_avg_content_length(self, collector):
        collector.search_index.add(CrawledPage(
            url="https://a.com",
            title="A",
            content="x" * 100,
        ))
        collector.search_index.add(CrawledPage(
            url="https://b.com",
            title="B",
            content="x" * 200,
        ))
        stats = collector.get_index_stats()
        assert stats.avg_content_length == pytest.approx(150.0)

    def test_oldest_newest_page(self, collector):
        collector.search_index.add(CrawledPage(
            url="https://a.com",
            title="A",
            content="Content",
            crawled_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        collector.search_index.add(CrawledPage(
            url="https://b.com",
            title="B",
            content="Content",
            crawled_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        ))
        stats = collector.get_index_stats()
        assert stats.oldest_page == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert stats.newest_page == datetime(2024, 6, 1, tzinfo=timezone.utc)


class TestGetIndexStatsDocPinning:
    """Pin the corrected get_index_stats docstring claim.

    The docstring now states: (a) a falsy search_index returns an all-default
    IndexStats (guard path), (b) top_domains/top_interests are capped to the
    top 10, and (c) oldest/newest are set only when timestamps exist. One
    returned object pins the main behavior and the guard path.
    """

    def test_guard_path_returns_all_defaults(self, interest_store):
        # Guard path: no search_index -> every field at its dataclass default.
        collector = StatsCollector(interest_store=interest_store)
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

    def test_top_domains_capped_at_10_and_oldest_newest_set(self, collector):
        # Main behavior: 12 distinct domains -> top_domains capped to 10.
        for i in range(12):
            collector.search_index.add(CrawledPage(
                url=f"https://d{i}.com/page",
                title=f"Page {i}",
                content="Some content here",
                crawled_at=datetime(
                    2024, 1, 1 + i, tzinfo=timezone.utc
                ),
            ))
        stats = collector.get_index_stats()
        assert stats.total_pages == 12
        assert len(stats.top_domains) == 10
        # oldest/newest set because timestamps exist.
        assert stats.oldest_page == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert stats.newest_page == datetime(2024, 1, 12, tzinfo=timezone.utc)
