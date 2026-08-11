"""Tests for the content scoring and ranking module."""

from datetime import datetime, timedelta

import pytest

from personal_index.content_scoring import (
    ContentScore,
    ContentScorer,
    ScoreFactor,
    ScoreWeights,
)


class TestScoreWeights:
    def test_default_weights(self) -> None:
        w = ScoreWeights()
        assert w.recency == 0.2
        assert w.relevance == 0.25
        assert w.engagement == 0.15
        assert w.quality == 0.15
        assert w.authority == 0.1
        assert w.freshness == 0.15

    def test_normalize_equal_weights(self) -> None:
        w = ScoreWeights(
            recency=1, relevance=1, engagement=1,
            quality=1, authority=1, freshness=1,
        )
        n = w.normalize()
        assert abs(sum([
            n.recency, n.relevance, n.engagement,
            n.quality, n.authority, n.freshness,
        ]) - 1.0) < 0.001

    def test_normalize_zero_weights(self) -> None:
        w = ScoreWeights(
            recency=0, relevance=0, engagement=0,
            quality=0, authority=0, freshness=0,
        )
        n = w.normalize()
        assert n.recency == 0.2  # Falls back to defaults

    def test_normalize_custom_weights(self) -> None:
        w = ScoreWeights(recency=0.5, relevance=0.5)
        n = w.normalize()
        assert abs(n.recency - 0.5) < 0.001
        assert abs(n.relevance - 0.5) < 0.001


class TestContentScore:
    def test_default_score(self) -> None:
        s = ContentScore()
        assert s.total == 0.0
        assert s.factors == {}

    def test_to_dict(self) -> None:
        s = ContentScore(
            total=0.75, recency=0.9, relevance=0.8,
            engagement=0.6, quality=0.7, authority=0.5,
            freshness=0.8,
        )
        d = s.to_dict()
        assert d["total"] == 0.75
        assert d["recency"] == 0.9
        assert isinstance(d["factors"], dict)


class TestContentScorer:
    def setup_method(self) -> None:
        self.scorer = ContentScorer()

    def test_score_all_defaults(self) -> None:
        result = self.scorer.score()
        assert isinstance(result, ContentScore)
        assert 0.0 <= result.total <= 1.0

    def test_score_perfect_relevance(self) -> None:
        result = self.scorer.score(
            keyword_matches=10, total_keywords=10,
        )
        assert result.relevance == 1.0

    def test_score_zero_relevance(self) -> None:
        result = self.scorer.score(
            keyword_matches=0, total_keywords=10,
        )
        assert result.relevance == 0.0

    def test_score_high_engagement(self) -> None:
        result = self.scorer.score(
            view_count=1000, bookmark_count=100, share_count=50,
        )
        assert result.engagement > 0.5

    def test_score_low_engagement(self) -> None:
        result = self.scorer.score(
            view_count=0, bookmark_count=0, share_count=0,
        )
        assert result.engagement == 0.0

    def test_score_quality_with_images(self) -> None:
        result = self.scorer.score(
            word_count=1000, has_images=True,
        )
        assert result.quality > self.scorer.score(word_count=1000).quality

    def test_score_authority_verified(self) -> None:
        result = self.scorer.score(
            domain_authority=0.8, is_verified_source=True,
        )
        assert result.authority > self.scorer.score(
            domain_authority=0.8, is_verified_source=False,
        ).authority

    def test_score_recency_new_content(self) -> None:
        now = datetime.now()
        result = self.scorer.score(published_at=now)
        assert result.recency > 0.9

    def test_score_recency_old_content(self) -> None:
        old = datetime.now() - timedelta(days=365)
        result = self.scorer.score(published_at=old)
        assert result.recency < 0.1

    def test_custom_weights(self) -> None:
        weights = ScoreWeights(relevance=1.0)
        scorer = ContentScorer(weights=weights)
        result = scorer.score(keyword_matches=5, total_keywords=5)
        assert result.total == pytest.approx(1.0, abs=0.01)

    def test_rank_returns_sorted(self) -> None:
        items = [
            {"keyword_matches": 10, "total_keywords": 10},
            {"keyword_matches": 0, "total_keywords": 10},
            {"keyword_matches": 5, "total_keywords": 10},
        ]
        ranked = self.scorer.rank(items)
        assert len(ranked) == 3
        assert ranked[0][1].total >= ranked[1][1].total
        assert ranked[1][1].total >= ranked[2][1].total

    def test_rank_limit(self) -> None:
        items = [{"keyword_matches": i, "total_keywords": 10} for i in range(20)]
        ranked = self.scorer.rank(items, limit=5)
        assert len(ranked) == 5

    def test_score_freshness_never(self) -> None:
        result = self.scorer.score(
            last_crawled=datetime.now(), change_frequency="never",
        )
        assert result.freshness == 1.0

    def test_score_freshness_recent(self) -> None:
        result = self.scorer.score(
            last_crawled=datetime.now(), change_frequency="daily",
        )
        assert result.freshness > 0.9

    def test_score_freshness_stale(self) -> None:
        old = datetime.now() - timedelta(days=100)
        result = self.scorer.score(
            last_crawled=old, change_frequency="daily",
        )
        assert result.freshness < 0.5
