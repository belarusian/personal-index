"""Tests for content metrics tracking."""

import pytest
from personal_index.content_metrics import (
    ContentMetrics,
    ContentMetricsTracker,
    ContentMetricsSummary,
    MetricsTimeRange,
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
