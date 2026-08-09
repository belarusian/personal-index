"""Tests for content analytics module."""

import pytest
from personal_index.content_analytics import (
    ContentAnalytics,
    EngagementScore,
    ContentCategory,
    AnalyticsReport,
)


class TestEngagementScore:
    def test_default_engagement_score(self):
        score = EngagementScore()
        assert score.total_score == 0.0
        assert score.view_count == 0
        assert score.bookmark_count == 0
        assert score.share_count == 0

    def test_engagement_score_from_values(self):
        score = EngagementScore(
            view_count=100,
            bookmark_count=10,
            share_count=5,
            comment_count=3,
            avg_time_on_page=120,
        )
        assert score.total_score > 0
        assert score.view_count == 100

    def test_engagement_score_weights(self):
        score = EngagementScore(
            view_count=100,
            bookmark_count=10,
            share_count=5,
            comment_count=3,
            avg_time_on_page=120,
        )
        # Verify score is computed from weighted components
        assert score.total_score == pytest.approx(
            100 * 0.1 + 10 * 0.3 + 5 * 0.5 + 3 * 0.4 + 120 * 0.01,
            abs=0.01,
        )

    def test_engagement_score_zero_views(self):
        score = EngagementScore(
            view_count=0,
            bookmark_count=5,
            share_count=2,
        )
        assert score.total_score > 0

    def test_engagement_score_to_dict(self):
        score = EngagementScore(view_count=50, bookmark_count=5)
        d = score.to_dict()
        assert "total_score" in d
        assert "view_count" in d


class TestContentCategory:
    def test_create_category(self):
        cat = ContentCategory(name="Technology", count=10)
        assert cat.name == "Technology"
        assert cat.count == 10

    def test_category_percentage(self):
        cat = ContentCategory(name="Tech", count=10, total=100)
        assert cat.percentage == 10.0

    def test_category_zero_total(self):
        cat = ContentCategory(name="Tech", count=10, total=0)
        assert cat.percentage == 0.0

    def test_category_to_dict(self):
        cat = ContentCategory(name="Tech", count=10, total=100)
        d = cat.to_dict()
        assert d["name"] == "Tech"
        assert d["count"] == 10
        assert d["percentage"] == 10.0


class TestContentAnalytics:
    def test_add_item(self):
        analytics = ContentAnalytics()
        analytics.add_item({"url": "https://a.com", "title": "Page A"})
        assert len(analytics._items) == 1

    def test_analyze_engagement(self):
        analytics = ContentAnalytics()
        analytics.add_item({
            "url": "https://a.com",
            "view_count": 100,
            "bookmark_count": 10,
            "share_count": 5,
        })
        scores = analytics.analyze_engagement()
        assert len(scores) == 1
        assert scores[0].total_score > 0

    def test_analyze_engagement_empty(self):
        analytics = ContentAnalytics()
        scores = analytics.analyze_engagement()
        assert len(scores) == 0

    def test_categorize(self):
        analytics = ContentAnalytics()
        analytics.add_item({"url": "https://a.com", "category": "Tech"})
        analytics.add_item({"url": "https://b.com", "category": "Tech"})
        analytics.add_item({"url": "https://c.com", "category": "Science"})
        cats = analytics.categorize()
        assert len(cats) == 2
        assert cats[0].name == "Tech"
        assert cats[0].count == 2

    def test_categorize_uncategorized(self):
        analytics = ContentAnalytics()
        analytics.add_item({"url": "https://a.com"})
        cats = analytics.categorize()
        assert len(cats) == 1
        assert cats[0].name == "Uncategorized"

    def test_generate_report(self):
        analytics = ContentAnalytics()
        analytics.add_item({
            "url": "https://a.com",
            "title": "Page A",
            "view_count": 100,
            "bookmark_count": 10,
            "share_count": 5,
            "category": "Tech",
        })
        report = analytics.generate_report()
        assert report.total_items == 1
        assert report.total_views == 100
        assert report.total_bookmarks == 10
        assert report.total_shares == 5

    def test_generate_report_empty(self):
        analytics = ContentAnalytics()
        report = analytics.generate_report()
        assert report.total_items == 0

    def test_generate_report_to_dict(self):
        analytics = ContentAnalytics()
        analytics.add_item({
            "url": "https://a.com",
            "title": "Page A",
            "view_count": 50,
            "bookmark_count": 5,
            "category": "Tech",
        })
        report = analytics.generate_report()
        d = report.to_dict()
        assert d["total_items"] == 1
        assert "top_categories" in d
        assert "top_engaged" in d

    def test_engagement_distribution(self):
        analytics = ContentAnalytics()
        # Low engagement
        analytics.add_item({"url": "https://a.com", "view_count": 1, "bookmark_count": 0})
        # Medium engagement
        analytics.add_item({"url": "https://b.com", "view_count": 50, "bookmark_count": 5})
        # High engagement
        analytics.add_item({"url": "https://c.com", "view_count": 200, "bookmark_count": 50, "share_count": 30})
        report = analytics.generate_report()
        assert report.engagement_distribution["low"] >= 1
        assert report.engagement_distribution["high"] >= 1
