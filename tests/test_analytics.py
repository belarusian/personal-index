"""Tests for analytics module."""

from __future__ import annotations

from personal_index.analytics import (
    AnalyticsData,
    AnalyticsTracker,
    CrawlEvent,
    SearchEvent,
)


class TestSearchEvent:
    """Tests for SearchEvent dataclass."""

    def test_create_event(self):
        e = SearchEvent(query="python", result_count=5)
        assert e.query == "python"
        assert e.result_count == 5
        assert e.timestamp

    def test_defaults(self):
        e = SearchEvent(query="test")
        assert e.result_count == 0
        assert e.clicked_url is None
        assert e.duration_ms == 0.0


class TestCrawlEvent:
    """Tests for CrawlEvent dataclass."""

    def test_create_event(self):
        e = CrawlEvent(url="http://example.com", status_code=200)
        assert e.url == "http://example.com"
        assert e.status_code == 200
        assert e.timestamp

    def test_with_error(self):
        e = CrawlEvent(url="http://example.com", status_code=500, error="timeout")
        assert e.error == "timeout"


class TestAnalyticsData:
    """Tests for AnalyticsData dataclass."""

    def test_defaults(self):
        data = AnalyticsData()
        assert data.total_searches == 0
        assert data.total_crawls == 0
        assert data.top_queries == []
        assert data.top_domains == []


class TestAnalyticsTracker:
    """Tests for AnalyticsTracker class."""

    def setup_method(self):
        self.tracker = AnalyticsTracker()

    def test_record_search(self):
        event = self.tracker.record_search("python", result_count=10)
        assert event.query == "python"
        assert event.result_count == 10

    def test_record_crawl(self):
        event = self.tracker.record_crawl("http://example.com", status_code=200)
        assert event.url == "http://example.com"
        assert event.status_code == 200

    def test_get_analytics_empty(self):
        data = self.tracker.get_analytics()
        assert data.total_searches == 0
        assert data.total_crawls == 0

    def test_get_analytics_with_searches(self):
        self.tracker.record_search("python", result_count=5)
        self.tracker.record_search("rust", result_count=3)
        self.tracker.record_search("python", result_count=8)

        data = self.tracker.get_analytics()
        assert data.total_searches == 3
        assert data.top_queries[0] == ("python", 2)
        assert data.top_queries[1] == ("rust", 1)

    def test_get_analytics_with_crawls(self):
        self.tracker.record_crawl("http://example.com/page1", status_code=200)
        self.tracker.record_crawl("http://example.com/page2", status_code=200)
        self.tracker.record_crawl("http://other.com/page", status_code=404)

        data = self.tracker.get_analytics()
        assert data.total_crawls == 3
        assert data.success_count == 2
        assert data.error_count == 1
        assert data.top_domains[0][0] == "example.com"
        assert data.top_domains[0][1] == 2

    def test_avg_search_duration(self):
        self.tracker.record_search("q1", duration_ms=100)
        self.tracker.record_search("q2", duration_ms=200)
        self.tracker.record_search("q3", duration_ms=300)

        data = self.tracker.get_analytics()
        assert data.avg_search_duration_ms == 200.0

    def test_avg_crawl_duration(self):
        self.tracker.record_crawl("http://a.com", duration_ms=50)
        self.tracker.record_crawl("http://b.com", duration_ms=150)

        data = self.tracker.get_analytics()
        assert data.avg_crawl_duration_ms == 100.0

    def test_hourly_searches(self):
        self.tracker.record_search("q1")
        self.tracker.record_search("q2")

        data = self.tracker.get_analytics()
        assert len(data.hourly_searches) > 0

    def test_daily_searches(self):
        self.tracker.record_search("q1")

        data = self.tracker.get_analytics()
        assert len(data.daily_searches) > 0

    def test_get_search_events(self):
        self.tracker.record_search("q1")
        self.tracker.record_search("q2")
        self.tracker.record_search("q3")

        events = self.tracker.get_search_events(limit=2)
        assert len(events) == 2
        assert events[0].query == "q2"

    def test_get_search_events_all(self):
        self.tracker.record_search("q1")
        self.tracker.record_search("q2")

        events = self.tracker.get_search_events()
        assert len(events) == 2

    def test_get_crawl_events(self):
        self.tracker.record_crawl("http://a.com")
        self.tracker.record_crawl("http://b.com")

        events = self.tracker.get_crawl_events(limit=1)
        assert len(events) == 1

    def test_get_search_stats_empty(self):
        stats = self.tracker.get_search_stats()
        assert stats["total"] == 0

    def test_get_search_stats(self):
        self.tracker.record_search("q1", result_count=5, duration_ms=100)
        self.tracker.record_search("q2", result_count=10, duration_ms=200)
        self.tracker.record_search("q1", result_count=3, duration_ms=150, clicked_url="http://x.com")

        stats = self.tracker.get_search_stats()
        assert stats["total"] == 3
        assert stats["unique_queries"] == 2
        assert stats["max_results"] == 10
        assert stats["min_results"] == 3
        assert stats["click_through_rate"] > 0

    def test_get_crawl_stats_empty(self):
        stats = self.tracker.get_crawl_stats()
        assert stats["total"] == 0

    def test_get_crawl_stats(self):
        self.tracker.record_crawl("http://a.com", status_code=200, content_size=1000, duration_ms=50)
        self.tracker.record_crawl("http://b.com", status_code=404, content_size=0, duration_ms=100, error="not found")

        stats = self.tracker.get_crawl_stats()
        assert stats["total"] == 2
        assert stats["total_content_size"] == 1000
        assert stats["error_rate"] == 0.5
        assert 200 in stats["status_codes"]
        assert 404 in stats["status_codes"]

    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "analytics.json")
        self.tracker.record_search("python", result_count=5)
        self.tracker.record_crawl("http://example.com", status_code=200)
        self.tracker.save(path)

        tracker2 = AnalyticsTracker()
        loaded = tracker2.load(path)
        assert loaded == 2
        assert tracker2.get_analytics().total_searches == 1
        assert tracker2.get_analytics().total_crawls == 1

    def test_load_nonexistent(self):
        loaded = self.tracker.load("/tmp/nonexistent_analytics.json")
        assert loaded == 0

    def test_clear(self):
        self.tracker.record_search("q1")
        self.tracker.record_crawl("http://a.com")
        self.tracker.clear()
        assert self.tracker.get_analytics().total_searches == 0
        assert self.tracker.get_analytics().total_crawls == 0

    def test_top_n_limit(self):
        for i in range(20):
            self.tracker.record_search(f"query_{i}")
        data = self.tracker.get_analytics(top_n=5)
        assert len(data.top_queries) == 5

    def test_extract_domain(self):
        assert AnalyticsTracker._extract_domain("http://example.com/path") == "example.com"
        assert AnalyticsTracker._extract_domain("https://test.org") == "test.org"
        assert AnalyticsTracker._extract_domain("") is None
        assert AnalyticsTracker._extract_domain(None) is None

    def test_search_with_click_tracking(self):
        self.tracker.record_search("python", clicked_url="http://docs.python.org")
        events = self.tracker.get_search_events()
        assert events[0].clicked_url == "http://docs.python.org"

    def test_crawl_with_error(self):
        self.tracker.record_crawl("http://bad.com", status_code=500, error="connection refused")
        events = self.tracker.get_crawl_events()
        assert events[0].error == "connection refused"
        assert events[0].status_code == 500
