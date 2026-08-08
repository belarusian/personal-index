"""Tests for content scoring module."""

import pytest
from personal_index.content_scoring import (
    ContentScore,
    ContentScorer,
    ScoreFactors,
)


class TestScoreFactors:
    def test_default_values(self):
        f = ScoreFactors()
        assert f.text_length == 0
        assert f.keyword_density == 0.0
        assert f.domain_reputation == 0.5

    def test_custom_values(self):
        f = ScoreFactors(text_length=500, keyword_density=0.15, bookmark_count=3)
        assert f.text_length == 500
        assert f.keyword_density == 0.15
        assert f.bookmark_count == 3


class TestContentScore:
    def test_default_score(self):
        s = ContentScore()
        assert s.total_score == 0.0

    def test_to_dict(self):
        s = ContentScore(total_score=0.75, text_quality=0.8)
        d = s.to_dict()
        assert d["total_score"] == 0.75
        assert d["text_quality"] == 0.8


class TestContentScorer:
    def test_scorer_default_weights(self):
        s = ContentScorer()
        assert s.WEIGHT_TEXT_QUALITY == 0.25
        assert s.WEIGHT_ENGAGEMENT == 0.25

    def test_scorer_custom_weights(self):
        s = ContentScorer(weights={"text_quality": 0.4, "engagement": 0.1})
        assert s.WEIGHT_TEXT_QUALITY == 0.4
        assert s.WEIGHT_ENGAGEMENT == 0.1

    def test_score_empty_factors(self):
        s = ContentScorer()
        result = s.score(ScoreFactors())
        assert result.total_score >= 0
        assert result.text_quality == 0.0

    def test_score_good_content(self):
        s = ContentScorer()
        factors = ScoreFactors(
            text_length=1500,
            keyword_density=0.12,
            tag_count=5,
            bookmark_count=3,
            visit_count=10,
            freshness_days=5,
            domain_reputation=0.9,
            content_type_score=0.8,
            link_count=15,
            image_count=3,
            has_summary=True,
            has_tags=True,
        )
        result = s.score(factors)
        assert result.total_score > 0.3
        assert result.text_quality > 0.5
        assert result.engagement > 0.3

    def test_score_fresh_vs_old(self):
        s = ContentScorer()
        fresh = s.score(ScoreFactors(freshness_days=1))
        old = s.score(ScoreFactors(freshness_days=365))
        assert fresh.freshness > old.freshness

    def test_score_engagement_scaling(self):
        s = ContentScorer()
        low = s.score(ScoreFactors(bookmark_count=0, visit_count=0, tag_count=0))
        high = s.score(ScoreFactors(bookmark_count=10, visit_count=100, tag_count=20))
        assert high.engagement > low.engagement

    def test_score_authority(self):
        s = ContentScorer()
        low_auth = s.score(ScoreFactors(domain_reputation=0.1, content_type_score=0.1))
        high_auth = s.score(ScoreFactors(domain_reputation=0.95, content_type_score=0.95))
        assert high_auth.authority > low_auth.authority

    def test_score_completeness(self):
        s = ContentScorer()
        incomplete = s.score(ScoreFactors(has_summary=False, has_tags=False, link_count=0, image_count=0))
        complete = s.score(ScoreFactors(has_summary=True, has_tags=True, link_count=30, image_count=15))
        assert complete.completeness > incomplete.completeness

    def test_score_batch(self):
        s = ContentScorer()
        factors = [ScoreFactors(text_length=100), ScoreFactors(text_length=2000)]
        results = s.score_batch(factors)
        assert len(results) == 2
        assert results[1].total_score > results[0].total_score

    def test_rank_descending(self):
        s = ContentScorer()
        factors = [
            ScoreFactors(text_length=100),
            ScoreFactors(text_length=2000),
            ScoreFactors(text_length=500),
        ]
        scores = s.score_batch(factors)
        ranked = s.rank(scores)
        assert ranked[0][1].total_score >= ranked[1][1].total_score

    def test_rank_ascending(self):
        s = ContentScorer()
        factors = [
            ScoreFactors(text_length=2000),
            ScoreFactors(text_length=100),
        ]
        scores = s.score_batch(factors)
        ranked = s.rank(scores, descending=False)
        assert ranked[0][1].total_score <= ranked[1][1].total_score

    def test_sigmoid_length_zero(self):
        s = ContentScorer()
        assert s._sigmoid_length(0) == 0.0
        assert s._sigmoid_length(-10) == 0.0

    def test_sigmoid_length_optimal(self):
        s = ContentScorer()
        score = s._sigmoid_length(s.OPTIMAL_LENGTH)
        assert abs(score - 0.5) < 0.01

    def test_sigmoid_length_very_long(self):
        s = ContentScorer()
        score = s._sigmoid_length(100000)
        assert score > 0.9

    def test_freshness_half_life(self):
        s = ContentScorer()
        score_30 = s._score_freshness(ScoreFactors(freshness_days=30))
        assert 0.45 < score_30 < 0.55

    def test_freshness_zero_days(self):
        s = ContentScorer()
        score = s._score_freshness(ScoreFactors(freshness_days=0))
        assert score == 1.0
