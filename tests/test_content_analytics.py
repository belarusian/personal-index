"""Tests for content analytics module."""

from datetime import datetime, timezone

import pytest

from personal_index.content_analytics.stats import ContentStats
from personal_index.content_analytics.trends import TrendAnalyzer, TrendPoint
from personal_index.content_analytics.insights import InsightEngine, Insight


class TestContentStats:
    def test_empty_items(self) -> None:
        stats = ContentStats.compute([])
        assert stats.total_items == 0
        assert stats.total_tags == 0
        assert stats.avg_score == 0.0

    def test_basic_stats(self) -> None:
        items = [
            {"type": "article", "tags": ["python"], "score": 0.8},
            {"type": "article", "tags": ["python", "web"], "score": 0.9},
            {"type": "video", "tags": ["web"], "score": 0.7},
        ]
        stats = ContentStats.compute(items)
        assert stats.total_items == 3
        assert stats.total_tags == 2
        assert stats.avg_score == pytest.approx(0.8, abs=0.01)
        assert stats.items_by_type["article"] == 2
        assert stats.items_by_type["video"] == 1
        assert stats.items_by_tag["python"] == 2
        assert stats.items_by_tag["web"] == 2

    def test_date_range(self) -> None:
        now = datetime.now(timezone.utc)
        items = [
            {"created_at": now.replace(day=1), "score": 0.5},
            {"created_at": now.replace(day=15), "score": 0.8},
        ]
        stats = ContentStats.compute(items)
        assert stats.oldest_item is not None
        assert stats.newest_item is not None
        assert stats.oldest_item < stats.newest_item

    def test_no_scores(self) -> None:
        items = [{"type": "article"}, {"type": "video"}]
        stats = ContentStats.compute(items)
        assert stats.avg_score == 0.0


class TestTrendAnalyzer:
    def test_volume_trend_empty(self) -> None:
        analyzer = TrendAnalyzer()
        assert analyzer.analyze_volume_trend([]) == []

    def test_volume_trend(self) -> None:
        items = [
            {"created_at": datetime(2024, 1, 1)},
            {"created_at": datetime(2024, 1, 1)},
            {"created_at": datetime(2024, 1, 2)},
        ]
        analyzer = TrendAnalyzer()
        trend = analyzer.analyze_volume_trend(items)
        assert len(trend) == 2
        assert trend[0].value == 2
        assert trend[1].value == 1

    def test_score_trend(self) -> None:
        items = [
            {"created_at": datetime(2024, 1, 1), "score": 0.5},
            {"created_at": datetime(2024, 1, 1), "score": 0.9},
            {"created_at": datetime(2024, 1, 2), "score": 0.7},
        ]
        analyzer = TrendAnalyzer()
        trend = analyzer.analyze_score_trend(items)
        assert len(trend) == 2
        assert trend[0].value == pytest.approx(0.7, abs=0.01)
        assert trend[1].value == pytest.approx(0.7, abs=0.01)

    def test_detect_anomalies(self) -> None:
        trend = [
            TrendPoint(datetime(2024, 1, i), float(i))
            for i in range(1, 11)
        ]
        trend.append(TrendPoint(datetime(2024, 1, 11), 100.0))
        analyzer = TrendAnalyzer()
        anomalies = analyzer.detect_anomalies(trend)
        assert len(anomalies) >= 1
        assert anomalies[0].value == 100.0

    def test_detect_anomalies_no_anomaly(self) -> None:
        trend = [
            TrendPoint(datetime(2024, 1, i), 5.0)
            for i in range(1, 11)
        ]
        analyzer = TrendAnalyzer()
        anomalies = analyzer.detect_anomalies(trend)
        assert anomalies == []


class TestInsightEngine:
    def test_insights_empty(self) -> None:
        engine = InsightEngine()
        assert engine.generate_insights([]) == []

    def test_insights_below_threshold(self) -> None:
        engine = InsightEngine(min_items_for_insight=10)
        items = [{"type": "article", "tags": ["a"], "score": 0.5} for _ in range(5)]
        assert engine.generate_insights(items) == []

    def test_tag_insight(self) -> None:
        items = [
            {"type": "article", "tags": ["python"], "score": 0.5}
            for _ in range(10)
        ]
        engine = InsightEngine()
        insights = engine.generate_insights(items)
        tag_insights = [i for i in insights if i.category == "tags"]
        assert len(tag_insights) == 1
        assert "python" in tag_insights[0].description

    def test_score_insight(self) -> None:
        items = [
            {"type": "article", "tags": ["a"], "score": 0.9}
            for _ in range(10)
        ]
        engine = InsightEngine()
        insights = engine.generate_insights(items)
        score_insights = [i for i in insights if i.category == "scoring"]
        assert len(score_insights) >= 1

    def test_low_quality_warning(self) -> None:
        items = [
            {"type": "article", "tags": ["a"], "score": 0.1}
            for _ in range(10)
        ]
        engine = InsightEngine()
        insights = engine.generate_insights(items)
        warnings = [i for i in insights if i.severity == "warning"]
        assert len(warnings) >= 1
