"""Tests for content metrics tracking."""

import pytest
from personal_index.content_metrics import (
    ContentMetrics,
    ContentMetricsTracker,
)


class TestContentMetrics:
    def test_create_basic_metrics(self):
        m = ContentMetrics(
            url="https://example.com/page1",
            title="Test Page",
            word_count=150,
            reading_time_seconds=90,
        )
        assert m.url == "https://example.com/page1"
        assert m.title == "Test Page"
        assert m.word_count == 150
        assert m.reading_time_seconds == 90

    def test_default_values(self):
        m = ContentMetrics(url="https://example.com")
        assert m.word_count == 0
        assert m.reading_time_seconds == 0
        assert m.char_count == 0
        assert m.sentence_count == 0
        assert m.paragraph_count == 0
        assert m.link_count == 0
        assert m.image_count == 0
        assert m.code_block_count == 0
        assert m.avg_word_length == 0.0
        assert m.unique_word_ratio == 0.0
        assert m.readability_score == 0.0

    def test_reading_time_default_calculation(self):
        m = ContentMetrics(url="https://example.com", word_count=200)
        # Default reading speed is 200 wpm
        assert m.reading_time_seconds == 60

    def test_reading_time_custom_speed(self):
        m = ContentMetrics(
            url="https://example.com",
            word_count=200,
            reading_speed_wpm=100,
        )
        assert m.reading_time_seconds == 120

    def test_to_dict(self):
        m = ContentMetrics(
            url="https://example.com",
            title="Test",
            word_count=100,
            reading_time_seconds=30,
        )
        d = m.to_dict()
        assert d["url"] == "https://example.com"
        assert d["word_count"] == 100
        assert "timestamp" in d

    def test_reading_time_minutes(self):
        m = ContentMetrics(url="https://example.com", word_count=600)
        assert m.reading_time_minutes() == 3.0

    def test_reading_time_minutes_partial(self):
        m = ContentMetrics(url="https://example.com", word_count=300)
        assert m.reading_time_minutes() == 1.5


class TestContentMetricsTracker:
    def test_init(self):
        tracker = ContentMetricsTracker()
        assert tracker._metrics == {}

    def test_record_metrics(self):
        tracker = ContentMetricsTracker()
        m = ContentMetrics(url="https://example.com", word_count=100)
        tracker.record(m)
        assert "https://example.com" in tracker._metrics

    def test_get_metrics(self):
        tracker = ContentMetricsTracker()
        m = ContentMetrics(url="https://example.com", word_count=100)
        tracker.record(m)
        result = tracker.get("https://example.com")
        assert result is not None
        assert result.word_count == 100

    def test_get_missing_metrics(self):
        tracker = ContentMetricsTracker()
        result = tracker.get("https://nonexistent.com")
        assert result is None

    def test_update_metrics(self):
        tracker = ContentMetricsTracker()
        m1 = ContentMetrics(url="https://example.com", word_count=100)
        tracker.record(m1)
        m2 = ContentMetrics(url="https://example.com", word_count=200)
        tracker.record(m2)
        result = tracker.get("https://example.com")
        assert result.word_count == 200

    def test_all_metrics(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100))
        tracker.record(ContentMetrics(url="https://b.com", word_count=200))
        all_m = tracker.all()
        assert len(all_m) == 2

    def test_remove_metrics(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://example.com", word_count=100))
        tracker.remove("https://example.com")
        assert tracker.get("https://example.com") is None

    def test_clear_metrics(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100))
        tracker.record(ContentMetrics(url="https://b.com", word_count=200))
        tracker.clear()
        assert len(tracker.all()) == 0

    def test_count(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100))
        tracker.record(ContentMetrics(url="https://b.com", word_count=200))
        assert tracker.count() == 2

    def test_count_empty(self):
        tracker = ContentMetricsTracker()
        assert tracker.count() == 0


class TestContentMetricsSummary:
    def test_summary_empty(self):
        tracker = ContentMetricsTracker()
        summary = tracker.summary()
        assert summary.total_items == 0
        assert summary.total_word_count == 0
        assert summary.avg_word_count == 0.0
        assert summary.total_reading_time_seconds == 0

    def test_summary_with_items(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100))
        tracker.record(ContentMetrics(url="https://b.com", word_count=300))
        summary = tracker.summary()
        assert summary.total_items == 2
        assert summary.total_word_count == 400
        assert summary.avg_word_count == 200.0
        assert summary.total_reading_time_seconds == 120

    def test_summary_max_min_word_count(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=50))
        tracker.record(ContentMetrics(url="https://b.com", word_count=500))
        tracker.record(ContentMetrics(url="https://c.com", word_count=250))
        summary = tracker.summary()
        assert summary.max_word_count == 500
        assert summary.min_word_count == 50

    def test_summary_median_word_count(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100))
        tracker.record(ContentMetrics(url="https://b.com", word_count=200))
        tracker.record(ContentMetrics(url="https://c.com", word_count=300))
        summary = tracker.summary()
        assert summary.median_word_count == 200.0

    def test_summary_median_even_count(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100))
        tracker.record(ContentMetrics(url="https://b.com", word_count=300))
        summary = tracker.summary()
        assert summary.median_word_count == 200.0


class TestMetricsTimeRange:
    def test_time_range_filter(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100, timestamp=1000.0))
        tracker.record(ContentMetrics(url="https://b.com", word_count=200, timestamp=2000.0))
        tracker.record(ContentMetrics(url="https://c.com", word_count=300, timestamp=3000.0))
        result = tracker.filter_by_time_range(1500.0, 2500.0)
        assert len(result) == 1
        assert result[0].url == "https://b.com"

    def test_time_range_filter_empty(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100, timestamp=1000.0))
        result = tracker.filter_by_time_range(5000.0, 6000.0)
        assert len(result) == 0

    def test_time_range_filter_all(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=100, timestamp=1000.0))
        tracker.record(ContentMetrics(url="https://b.com", word_count=200, timestamp=2000.0))
        result = tracker.filter_by_time_range(0.0, 9999.0)
        assert len(result) == 2

    def test_sort_by_word_count(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=300))
        tracker.record(ContentMetrics(url="https://b.com", word_count=100))
        tracker.record(ContentMetrics(url="https://c.com", word_count=200))
        result = tracker.sort_by_word_count()
        assert result[0].word_count == 100
        assert result[1].word_count == 200
        assert result[2].word_count == 300

    def test_sort_by_reading_time(self):
        tracker = ContentMetricsTracker()
        tracker.record(ContentMetrics(url="https://a.com", word_count=300))
        tracker.record(ContentMetrics(url="https://b.com", word_count=100))
        result = tracker.sort_by_reading_time()
        assert result[0].url == "https://b.com"
        assert result[1].url == "https://a.com"
