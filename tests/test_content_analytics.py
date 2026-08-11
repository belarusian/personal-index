"""Tests for the content analytics module."""

from datetime import datetime

from personal_index.content_analytics import (
    AnalyticsEngine,
    ContentAnalytics,
)


class TestContentAnalytics:
    def test_to_dict(self) -> None:
        analytics = ContentAnalytics(
            total_items=100,
            unique_domains=10,
            unique_tags=25,
            avg_score=0.75,
            bookmarked_count=20,
        )
        d = analytics.to_dict()
        assert d["total_items"] == 100
        assert d["avg_score"] == 0.75


class TestAnalyticsEngine:
    def setup_method(self) -> None:
        self.engine = AnalyticsEngine()
        self.items = [
            {
                "id": str(i),
                "title": f"Article {i}",
                "url": f"https://example{i % 3}.com/article/{i}",
                "tags": ["python", "web"] if i % 2 == 0 else ["javascript"],
                "score": 0.5 + (i % 10) * 0.05,
                "word_count": 500 + i * 100,
                "bookmarked": i % 3 == 0,
                "published_at": datetime(2024, 1, 1 + (i % 7)),
            }
            for i in range(20)
        ]

    def test_analyze_empty(self) -> None:
        analytics = self.engine.analyze([])
        assert analytics.total_items == 0

    def test_analyze_total_items(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.total_items == 20

    def test_analyze_unique_domains(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.unique_domains == 3

    def test_analyze_top_domains(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert len(analytics.top_domains) > 0
        assert analytics.top_domains[0][0].startswith("example")

    def test_analyze_top_tags(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert len(analytics.top_tags) > 0

    def test_analyze_avg_score(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.avg_score > 0
        assert analytics.avg_score < 1.0

    def test_analyze_score_distribution(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert "excellent (0.8-1.0)" in analytics.score_distribution

    def test_analyze_bookmarked(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.bookmarked_count > 0

    def test_analyze_tagged(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.tagged_count == 20  # All items have tags

    def test_analyze_dates(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.oldest_item is not None
        assert analytics.newest_item is not None
        assert analytics.oldest_item <= analytics.newest_item

    def test_analyze_daily_counts(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert len(analytics.daily_counts) > 0

    def test_analyze_avg_word_count(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.avg_word_count > 0

    def test_compare_periods(self) -> None:
        comparison = self.engine.compare_periods(
            self.items,
            period1_start=datetime(2024, 1, 1),
            period1_end=datetime(2024, 1, 3),
            period2_start=datetime(2024, 1, 4),
            period2_end=datetime(2024, 1, 7),
        )
        assert "period1" in comparison
        assert "period2" in comparison
        assert "changes" in comparison

    def test_analyze_to_dict(self) -> None:
        analytics = self.engine.analyze(self.items)
        d = analytics.to_dict()
        assert "total_items" in d
        assert "top_domains" in d
        assert "score_distribution" in d
