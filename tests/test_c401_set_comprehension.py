"""Tests for TICKET-74: C401 - set() wrapping generator rewritten as set comprehension."""

from personal_index.analytics import AnalyticsTracker, SearchEvent


class TestAnalyticsTracker:
    def test_search_stats_unique_queries(self):
        tracker = AnalyticsTracker()
        # Add some search events
        tracker.record_search(SearchEvent(query="test", result_count=5, duration_ms=100))
        tracker.record_search(SearchEvent(query="test", result_count=3, duration_ms=50))
        tracker.record_search(SearchEvent(query="other", result_count=2, duration_ms=75))
        stats = tracker.get_search_stats()
        assert stats["unique_queries"] == 2

    def test_search_stats_empty(self):
        tracker = AnalyticsTracker()
        stats = tracker.get_search_stats()
        # Empty case returns just {"total": 0}
        assert stats == {"total": 0}
