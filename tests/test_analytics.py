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

    def test_get_search_stats_fields_pinned(self):
        # Guard path: no events -> exactly {"total": 0}.
        empty = self.tracker.get_search_stats()
        assert empty == {"total": 0}

        # Normal path: pin every returned field against the returned object.
        self.tracker.record_search("q1", result_count=5, duration_ms=100)
        self.tracker.record_search("q2", result_count=10, duration_ms=200)
        self.tracker.record_search("q1", result_count=3, duration_ms=150,
                                   clicked_url="http://x.com")
        stats = self.tracker.get_search_stats()
        assert stats["total"] == 3
        assert stats["avg_results"] == (5 + 10 + 3) / 3
        assert stats["max_results"] == 10
        assert stats["min_results"] == 3
        assert stats["avg_duration_ms"] == (100 + 200 + 150) / 3
        assert stats["max_duration_ms"] == 200
        assert stats["click_through_rate"] == 1 / 3
        assert stats["unique_queries"] == 2

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

    def test_get_crawl_stats_fields_pinned(self):
        # Guard path: no events -> exactly {"total": 0}.
        empty = self.tracker.get_crawl_stats()
        assert empty == {"total": 0}

        # Normal path: pin every returned field against the returned object.
        # event3 has duration_ms=0 (filtered out of durations) and event2
        # has content_size=0 (filtered out of sizes) so the sub-component
        # filters are witnessed alongside the main behavior.
        self.tracker.record_crawl("http://a.com", status_code=200,
                                  content_size=1000, duration_ms=50)
        self.tracker.record_crawl("http://b.com", status_code=404,
                                  content_size=0, duration_ms=100,
                                  error="not found")
        self.tracker.record_crawl("http://c.com", status_code=200,
                                  content_size=500, duration_ms=0)
        stats = self.tracker.get_crawl_stats()
        assert stats["total"] == 3
        assert stats["avg_duration_ms"] == (50 + 100) / 2
        assert stats["avg_content_size"] == (1000 + 500) / 2
        assert stats["total_content_size"] == 1500
        assert stats["status_codes"] == {200: 2, 404: 1}
        assert stats["error_rate"] == 1 / 3


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

    def test_get_analytics_pins_merged_fields_and_empty_guard(self):
        # Normal case: both search and crawl events present.
        self.tracker.record_search("python", result_count=5, duration_ms=100)
        self.tracker.record_search("python", result_count=8, duration_ms=200)
        self.tracker.record_search("rust", result_count=3)
        self.tracker.record_crawl("http://example.com/a", status_code=200, duration_ms=50)
        self.tracker.record_crawl("http://example.com/b", status_code=200)
        self.tracker.record_crawl("http://other.com/c", status_code=404)

        data = self.tracker.get_analytics()
        # Search-source fields.
        assert data.total_searches == 3
        assert data.avg_search_duration_ms == 150.0
        assert data.top_queries[0] == ("python", 2)
        assert data.top_queries[1] == ("rust", 1)
        # Crawl-source fields.
        assert data.total_crawls == 3
        assert data.avg_crawl_duration_ms == 50.0
        assert data.top_domains[0] == ("example.com", 2)
        assert data.success_count == 2
        assert data.error_count == 1
        # total_pages_indexed is never set by either sub-compute.
        assert data.total_pages_indexed == 0

        # Guard path: empty tracker -> both sub-computes return defaults.
        empty = AnalyticsTracker().get_analytics()
        assert empty.total_searches == 0
        assert empty.total_crawls == 0
        assert empty.avg_search_duration_ms == 0.0
        assert empty.avg_crawl_duration_ms == 0.0
        assert empty.top_queries == []
        assert empty.top_domains == []
        assert empty.hourly_searches == {}
        assert empty.daily_searches == {}
        assert empty.error_count == 0
        assert empty.success_count == 0
        assert empty.total_pages_indexed == 0


class TestComputeSearchAnalytics:
    """Tests for _compute_search_analytics helper."""

    def setup_method(self):
        self.tracker = AnalyticsTracker()

    def test_empty_search_events(self):
        data = self.tracker._compute_search_analytics(10)
        assert data.total_searches == 0
        assert data.avg_search_duration_ms == 0.0
        assert data.top_queries == []
        assert data.hourly_searches == {}
        assert data.daily_searches == {}

    def test_search_analytics_with_events(self):
        self.tracker.record_search("python", result_count=5, duration_ms=100)
        self.tracker.record_search("rust", result_count=3, duration_ms=200)
        self.tracker.record_search("python", result_count=8, duration_ms=300)

        data = self.tracker._compute_search_analytics(10)
        assert data.total_searches == 3
        assert data.avg_search_duration_ms == 200.0
        assert data.top_queries[0] == ("python", 2)
        assert len(data.hourly_searches) > 0
        assert len(data.daily_searches) > 0

    def test_search_analytics_top_n(self):
        for i in range(20):
            self.tracker.record_search(f"query_{i}")
        data = self.tracker._compute_search_analytics(top_n=3)
        assert len(data.top_queries) == 3

    def test_search_analytics_crawl_fields_empty(self):
        """Search analytics should not populate crawl fields."""
        self.tracker.record_search("test")
        data = self.tracker._compute_search_analytics(10)
        assert data.total_crawls == 0
        assert data.top_domains == []
        assert data.success_count == 0
        assert data.error_count == 0


class TestComputeCrawlAnalytics:
    """Tests for _compute_crawl_analytics helper."""

    def setup_method(self):
        self.tracker = AnalyticsTracker()

    def test_empty_crawl_events(self):
        data = self.tracker._compute_crawl_analytics(10)
        assert data.total_crawls == 0
        assert data.avg_crawl_duration_ms == 0.0
        assert data.top_domains == []
        assert data.success_count == 0
        assert data.error_count == 0

    def test_crawl_analytics_with_events(self):
        self.tracker.record_crawl("http://example.com/page1", status_code=200, duration_ms=50)
        self.tracker.record_crawl("http://example.com/page2", status_code=200, duration_ms=150)
        self.tracker.record_crawl("http://other.com/page", status_code=404, duration_ms=100)

        data = self.tracker._compute_crawl_analytics(10)
        assert data.total_crawls == 3
        assert data.avg_crawl_duration_ms == 100.0
        assert data.top_domains[0][0] == "example.com"
        assert data.top_domains[0][1] == 2
        assert data.success_count == 2
        assert data.error_count == 1

    def test_crawl_analytics_top_n(self):
        for i in range(20):
            self.tracker.record_crawl(f"http://domain{i}.com/page")
        data = self.tracker._compute_crawl_analytics(top_n=5)
        assert len(data.top_domains) == 5

    def test_crawl_analytics_search_fields_empty(self):
        """Crawl analytics should not populate search fields."""
        self.tracker.record_crawl("http://example.com")
        data = self.tracker._compute_crawl_analytics(10)
        assert data.total_searches == 0
        assert data.top_queries == []
        assert data.hourly_searches == {}
        assert data.daily_searches == {}


class TestAnalyticsTrackerNonDictGuard:
    """load() must degrade to 0 on valid-JSON-but-wrong-type (non-dict) files."""

    def setup_method(self):
        self.tracker = AnalyticsTracker()

    def _write(self, tmp_path, content: str) -> str:
        path = str(tmp_path / "analytics.json")
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_load_null(self, tmp_path):
        path = self._write(tmp_path, "null")
        assert self.tracker.load(path) == 0
        assert self.tracker.get_analytics().total_searches == 0
        assert self.tracker.get_analytics().total_crawls == 0

    def test_load_number(self, tmp_path):
        path = self._write(tmp_path, "42")
        assert self.tracker.load(path) == 0

    def test_load_list(self, tmp_path):
        path = self._write(tmp_path, '[{"query": "x"}]')
        assert self.tracker.load(path) == 0

    def test_load_string(self, tmp_path):
        path = self._write(tmp_path, '"hello"')
        assert self.tracker.load(path) == 0

    def test_valid_dict_still_works(self, tmp_path):
        path = str(tmp_path / "analytics.json")
        self.tracker.record_search("python", result_count=5)
        self.tracker.record_crawl("http://example.com", status_code=200)
        self.tracker.save(path)

        tracker2 = AnalyticsTracker()
        assert tracker2.load(path) == 2
        assert tracker2.get_analytics().total_searches == 1
        assert tracker2.get_analytics().total_crawls == 1

    def test_valid_after_invalid_not_suppressed(self, tmp_path):
        path = str(tmp_path / "analytics.json")
        with open(path, "w") as f:
            f.write("null")
        assert self.tracker.load(path) == 0

        # overwrite with a valid dict; the guard must not suppress a later valid load
        self.tracker.record_search("rust", result_count=3)
        self.tracker.save(path)
        tracker2 = AnalyticsTracker()
        assert tracker2.load(path) == 1
        assert tracker2.get_analytics().total_searches == 1


class TestAnalyticsTrackerCorruptJsonGuard:
    """Regression: corrupt/truncated JSON in analytics file must not crash AnalyticsTracker.load."""

    def setup_method(self):
        self.tracker = AnalyticsTracker()

    def test_load_corrupt_brace_json(self, tmp_path):
        path = str(tmp_path / "analytics.json")
        with open(path, "w") as f:
            f.write("{")
        assert self.tracker.load(path) == 0
        assert self.tracker.get_analytics().total_searches == 0
        assert self.tracker.get_analytics().total_crawls == 0

    def test_load_truncated_json(self, tmp_path):
        path = str(tmp_path / "analytics.json")
        with open(path, "w") as f:
            f.write('{"search_events": [{"query": "http://exa')
        assert self.tracker.load(path) == 0
        assert self.tracker.get_analytics().total_searches == 0
        assert self.tracker.get_analytics().total_crawls == 0


class TestGetEventsDocPinning:
    """Pin the corrected get_search_events/get_crawl_events docstring claim.

    The docstring now states: a positive ``limit`` returns only the LAST
    ``limit`` events (the most recent tail); a falsy ``limit`` (``None`` or
    ``0``) returns all recorded events. These tests pin both the guard path
    (falsy limit -> all) and the main behavior (positive limit -> tail)
    against the returned list fields.
    """

    def setup_method(self):
        self.tracker = AnalyticsTracker()

    def test_search_events_falsy_limit_returns_all(self):
        # Guard path: limit=0 is falsy -> ALL events, in order.
        self.tracker.record_search("q1")
        self.tracker.record_search("q2")
        self.tracker.record_search("q3")
        events = self.tracker.get_search_events(limit=0)
        assert [e.query for e in events] == ["q1", "q2", "q3"]

    def test_search_events_positive_limit_returns_tail(self):
        # Main behavior: limit=2 -> the LAST 2 events (most recent tail).
        self.tracker.record_search("q1")
        self.tracker.record_search("q2")
        self.tracker.record_search("q3")
        events = self.tracker.get_search_events(limit=2)
        assert [e.query for e in events] == ["q2", "q3"]

    def test_crawl_events_falsy_limit_returns_all(self):
        # Guard path: limit=0 is falsy -> ALL crawl events, in order.
        self.tracker.record_crawl("http://a.com")
        self.tracker.record_crawl("http://b.com")
        self.tracker.record_crawl("http://c.com")
        events = self.tracker.get_crawl_events(limit=0)
        assert [e.url for e in events] == [
            "http://a.com",
            "http://b.com",
            "http://c.com",
        ]

    def test_crawl_events_positive_limit_returns_tail(self):
        # Main behavior: limit=1 -> the LAST crawl event (most recent tail).
        self.tracker.record_crawl("http://a.com")
        self.tracker.record_crawl("http://b.com")
        self.tracker.record_crawl("http://c.com")
        events = self.tracker.get_crawl_events(limit=1)
        assert [e.url for e in events] == ["http://c.com"]
