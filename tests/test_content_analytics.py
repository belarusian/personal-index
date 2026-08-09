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
