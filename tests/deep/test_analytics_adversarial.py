"""Adversarial deep tests for personal_index/analytics.py.

Probes: negative/zero top_n, empty event lists, malformed timestamps,
duplicate queries, unicode queries, duration edge cases.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest

from personal_index.analytics import (
    AnalyticsTracker,
    CrawlEvent,
    SearchEvent,
)


@pytest.fixture
def tracker() -> AnalyticsTracker:
    return AnalyticsTracker()


class TestTopNEdgeCases:
    """Probe top_n parameter edge cases."""

    def test_negative_top_n_returns_empty(self, tracker: AnalyticsTracker) -> None:
        """Negative top_n should return empty lists (Counter.most_common behavior)."""
        tracker.record_search("query1", result_count=5)
        tracker.record_search("query2", result_count=3)
        data = tracker.get_analytics(top_n=-5)
        assert data.top_queries == []
        assert data.top_domains == []

    def test_zero_top_n_returns_empty(self, tracker: AnalyticsTracker) -> None:
        """Zero top_n should return empty lists."""
        tracker.record_search("query1", result_count=5)
        data = tracker.get_analytics(top_n=0)
        assert data.top_queries == []

    def test_large_top_n_returns_all(self, tracker: AnalyticsTracker) -> None:
        """top_n larger than event count should return all."""
        tracker.record_search("query1", result_count=5)
        tracker.record_search("query2", result_count=3)
        data = tracker.get_analytics(top_n=100)
        assert len(data.top_queries) == 2


class TestEmptyEventLists:
    """Probe behavior with no events."""

    def test_analytics_with_no_events(self, tracker: AnalyticsTracker) -> None:
        """Analytics with no events should return zeros/empty."""
        data = tracker.get_analytics()
        assert data.total_searches == 0
        assert data.total_crawls == 0
        assert data.avg_search_duration_ms == 0.0
        assert data.avg_crawl_duration_ms == 0.0
        assert data.top_queries == []
        assert data.top_domains == []
        assert data.hourly_searches == {}
        assert data.daily_searches == {}

    def test_search_stats_with_no_events(self, tracker: AnalyticsTracker) -> None:
        """Search stats with no events should return total: 0."""
        stats = tracker.get_search_stats()
        assert stats == {"total": 0}

    def test_crawl_stats_with_no_events(self, tracker: AnalyticsTracker) -> None:
        """Crawl stats with no events should return total: 0."""
        stats = tracker.get_crawl_stats()
        assert stats == {"total": 0}


class TestMalformedTimestamps:
    """Probe behavior with invalid timestamps."""

    def test_search_with_invalid_timestamp(self, tracker: AnalyticsTracker) -> None:
        """Invalid timestamp should be silently skipped in hourly/daily."""
        tracker.record_search(SearchEvent(query="query1", result_count=5, timestamp="not-a-timestamp"))
        data = tracker.get_analytics()
        assert data.total_searches == 1
        assert data.hourly_searches == {}
        assert data.daily_searches == {}

    def test_crawl_with_invalid_timestamp(self, tracker: AnalyticsTracker) -> None:
        """Invalid timestamp should be silently skipped."""
        tracker._crawl_events.append(CrawlEvent(url="http://example.com", status_code=200, timestamp="invalid"))
        data = tracker.get_analytics()
        assert data.total_crawls == 1


class TestDuplicateQueries:
    """Probe behavior with duplicate search queries."""

    def test_duplicate_queries_counted_separately(self, tracker: AnalyticsTracker) -> None:
        """Duplicate queries should be counted in top_queries."""
        tracker.record_search("same query", result_count=5)
        tracker.record_search("same query", result_count=3)
        tracker.record_search("different", result_count=1)
        data = tracker.get_analytics(top_n=10)
        assert len(data.top_queries) == 2
        assert data.top_queries[0] == ("same query", 2)

    def test_case_sensitive_queries(self, tracker: AnalyticsTracker) -> None:
        """Queries should be case-sensitive."""
        tracker.record_search("Query", result_count=5)
        tracker.record_search("query", result_count=3)
        data = tracker.get_analytics(top_n=10)
        assert len(data.top_queries) == 2


class TestUnicodeQueries:
    """Probe behavior with unicode search queries."""

    def test_unicode_query(self, tracker: AnalyticsTracker) -> None:
        """Unicode queries should work."""
        tracker.record_search("测试查询", result_count=5)
        tracker.record_search("Tëst", result_count=3)
        data = tracker.get_analytics(top_n=10)
        assert len(data.top_queries) == 2

    def test_emoji_query(self, tracker: AnalyticsTracker) -> None:
        """Emoji queries should work."""
        tracker.record_search("🚀 rocket", result_count=5)
        data = tracker.get_analytics(top_n=10)
        assert len(data.top_queries) == 1
        assert data.top_queries[0][0] == "🚀 rocket"


class TestDurationEdgeCases:
    """Probe duration calculation edge cases."""

    def test_zero_duration_excluded_from_avg(self, tracker: AnalyticsTracker) -> None:
        """Zero durations should be excluded from average."""
        tracker.record_search("q1", result_count=5, duration_ms=0)
        tracker.record_search("q2", result_count=3, duration_ms=100)
        data = tracker.get_analytics()
        assert data.avg_search_duration_ms == 100.0

    def test_negative_duration_excluded_from_avg(self, tracker: AnalyticsTracker) -> None:
        """Negative durations should be excluded from average."""
        tracker.record_search("q1", result_count=5, duration_ms=-10)
        tracker.record_search("q2", result_count=3, duration_ms=100)
        data = tracker.get_analytics()
        assert data.avg_search_duration_ms == 100.0

    def test_all_zero_durations(self, tracker: AnalyticsTracker) -> None:
        """All zero durations should result in 0.0 average."""
        tracker.record_search("q1", result_count=5, duration_ms=0)
        tracker.record_search("q2", result_count=3, duration_ms=0)
        data = tracker.get_analytics()
        assert data.avg_search_duration_ms == 0.0


class TestSaveLoad:
    """Probe save/load round-trip."""

    def test_save_load_roundtrip(self, tracker: AnalyticsTracker) -> None:
        """Save and load should preserve events."""
        tracker.record_search("query1", result_count=5)
        tracker.record_crawl("http://example.com", status_code=200)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            tracker.save(path)
            new_tracker = AnalyticsTracker()
            loaded = new_tracker.load(path)
            assert loaded == 2
            assert new_tracker.get_analytics().total_searches == 1
            assert new_tracker.get_analytics().total_crawls == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_load_missing_file(self, tracker: AnalyticsTracker) -> None:
        """Loading missing file should return 0."""
        loaded = tracker.load("/nonexistent/path.json")
        assert loaded == 0

    def test_load_invalid_json(self, tracker: AnalyticsTracker) -> None:
        """Loading invalid JSON should return 0."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            path = f.name

        try:
            loaded = tracker.load(path)
            assert loaded == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestClear:
    """Probe clear behavior."""

    def test_clear_removes_all_events(self, tracker: AnalyticsTracker) -> None:
        """Clear should remove all events."""
        tracker.record_search("query1", result_count=5)
        tracker.record_crawl("http://example.com", status_code=200)
        tracker.clear()
        data = tracker.get_analytics()
        assert data.total_searches == 0
        assert data.total_crawls == 0


class TestGetEvents:
    """Probe get_search_events and get_crawl_events."""

    def test_get_search_events_limit(self, tracker: AnalyticsTracker) -> None:
        """Limit should return last N events."""
        tracker.record_search("q1", result_count=5)
        tracker.record_search("q2", result_count=3)
        tracker.record_search("q3", result_count=1)
        events = tracker.get_search_events(limit=2)
        assert len(events) == 2
        assert events[0].query == "q2"
        assert events[1].query == "q3"

    def test_get_search_events_no_limit(self, tracker: AnalyticsTracker) -> None:
        """No limit should return all events."""
        tracker.record_search("q1", result_count=5)
        tracker.record_search("q2", result_count=3)
        events = tracker.get_search_events()
        assert len(events) == 2

    def test_get_crawl_events_limit(self, tracker: AnalyticsTracker) -> None:
        """Limit should return last N crawl events."""
        tracker.record_crawl("http://example.com/1", status_code=200)
        tracker.record_crawl("http://example.com/2", status_code=200)
        tracker.record_crawl("http://example.com/3", status_code=200)
        events = tracker.get_crawl_events(limit=2)
        assert len(events) == 2
        assert events[0].url == "http://example.com/2"
        assert events[1].url == "http://example.com/3"
