"""Tests for personal_index.content_scoring module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from personal_index.content_scoring import (
    ContentScore,
    ContentScorer,
    ScoreWeights,
)

# ── ScoreWeights ───────────────────────────────────────────────────

class TestScoreWeights:
    """Tests for ScoreWeights dataclass."""

    def test_default_weights(self) -> None:
        w = ScoreWeights()
        assert w.recency == 0.2
        assert w.relevance == 0.25
        assert w.engagement == 0.15
        assert w.quality == 0.15
        assert w.authority == 0.1
        assert w.freshness == 0.15

    def test_normalize_custom_weights_sum_to_one(self) -> None:
        w = ScoreWeights(
            recency=0.5, relevance=0.5,
            engagement=0, quality=0, authority=0, freshness=0,
        )
        n = w.normalize()
        total = (
            n.recency + n.relevance + n.engagement
            + n.quality + n.authority + n.freshness
        )
        assert abs(total - 1.0) < 0.001

    def test_normalize_all_zero_falls_back_to_defaults(self) -> None:
        w = ScoreWeights(
            recency=0, relevance=0, engagement=0,
            quality=0, authority=0, freshness=0,
        )
        n = w.normalize()
        assert n.recency == 0.2
        assert n.relevance == 0.25
        assert n.engagement == 0.15
        assert n.quality == 0.15
        assert n.authority == 0.1
        assert n.freshness == 0.15

    def test_normalize_equal_weights(self) -> None:
        w = ScoreWeights(
            recency=1, relevance=1, engagement=1,
            quality=1, authority=1, freshness=1,
        )
        n = w.normalize()
        expected = 1.0 / 6
        assert abs(n.recency - expected) < 0.001
        assert abs(n.relevance - expected) < 0.001


# ── ContentScore ───────────────────────────────────────────────────

class TestContentScore:
    """Tests for ContentScore dataclass."""

    def test_default_values(self) -> None:
        s = ContentScore()
        assert s.total == 0.0
        assert s.recency == 0.0
        assert s.relevance == 0.0
        assert s.factors == {}

    def test_to_dict_serialization(self) -> None:
        s = ContentScore(
            total=0.75,
            recency=0.9,
            relevance=0.8,
            engagement=0.6,
            quality=0.7,
            authority=0.5,
            freshness=0.8,
        )
        d = s.to_dict()
        assert d["total"] == 0.75
        assert d["recency"] == 0.9
        assert d["relevance"] == 0.8
        assert d["engagement"] == 0.6
        assert d["quality"] == 0.7
        assert d["authority"] == 0.5
        assert d["freshness"] == 0.8
        assert isinstance(d["factors"], dict)

    def test_to_dict_rounds_values(self) -> None:
        s = ContentScore(total=0.123456789)
        d = s.to_dict()
        assert d["total"] == 0.1235


# ── ContentScorer ──────────────────────────────────────────────────

class TestContentScorer:
    """Tests for ContentScorer class."""

    @pytest.fixture
    def scorer(self) -> ContentScorer:
        return ContentScorer()

    # ── score() ──────────────────────────────────────────────────

    def test_score_default_weights(self, scorer: ContentScorer) -> None:
        result = scorer.score()
        assert isinstance(result, ContentScore)
        assert 0.0 <= result.total <= 1.0

    def test_score_all_factors_zero(self, scorer: ContentScorer) -> None:
        result = scorer.score(
            keyword_matches=0, total_keywords=10,
            view_count=0, bookmark_count=0, share_count=0,
            word_count=0,
            domain_authority=0.0,
        )
        assert result.relevance == 0.0
        assert result.engagement == 0.0
        assert result.quality == 0.0
        assert result.authority == 0.0

    def test_score_max_engagement(self, scorer: ContentScorer) -> None:
        result = scorer.score(
            view_count=1000, bookmark_count=1000, share_count=1000,
        )
        assert result.engagement > 0.5

    # ── _score_recency() ─────────────────────────────────────────

    def test_score_recency_new_content(self, scorer: ContentScorer) -> None:
        now = datetime.now(tz=timezone.utc)
        result = scorer.score(published_at=now)
        assert result.recency > 0.9

    def test_score_recency_old_content(self, scorer: ContentScorer) -> None:
        old = datetime.now(tz=timezone.utc) - timedelta(days=365)
        result = scorer.score(published_at=old)
        assert result.recency < 0.1

    def test_score_recency_no_date_defaults_to_now(self, scorer: ContentScorer) -> None:
        """When no date is provided, recency defaults to 1.0 (treated as now)."""
        result = scorer.score()
        assert result.recency == 1.0

    # ── _score_relevance() ───────────────────────────────────────

    def test_score_relevance_perfect_match(self, scorer: ContentScorer) -> None:
        result = scorer.score(keyword_matches=10, total_keywords=10)
        assert result.relevance == 1.0

    def test_score_relevance_no_match(self, scorer: ContentScorer) -> None:
        result = scorer.score(keyword_matches=0, total_keywords=10)
        assert result.relevance == 0.0

    def test_score_relevance_zero_total_keywords(self, scorer: ContentScorer) -> None:
        result = scorer.score(keyword_matches=0, total_keywords=0)
        assert result.relevance == 0.0

    def test_score_relevance_partial_match(self, scorer: ContentScorer) -> None:
        result = scorer.score(keyword_matches=5, total_keywords=10)
        assert result.relevance == 0.5

    # ── _score_engagement() ──────────────────────────────────────

    def test_score_engagement_log_scaling(self, scorer: ContentScorer) -> None:
        r1 = scorer.score(view_count=10).engagement
        r2 = scorer.score(view_count=100).engagement
        r3 = scorer.score(view_count=1000).engagement
        assert r1 < r2 < r3

    def test_score_engagement_zero_counts(self, scorer: ContentScorer) -> None:
        result = scorer.score(
            view_count=0, bookmark_count=0, share_count=0,
        )
        assert result.engagement == 0.0

    def test_score_engagement_high_views(self, scorer: ContentScorer) -> None:
        result = scorer.score(view_count=1000)
        assert result.engagement > 0.0

    # ── _score_quality() ─────────────────────────────────────────

    def test_score_quality_word_count_scaling(self, scorer: ContentScorer) -> None:
        r1 = scorer.score(word_count=100).quality
        r2 = scorer.score(word_count=1000).quality
        r3 = scorer.score(word_count=3000).quality
        assert r1 < r2 < r3

    def test_score_quality_image_bonus(self, scorer: ContentScorer) -> None:
        r_no_img = scorer.score(word_count=1000, has_images=False).quality
        r_img = scorer.score(word_count=1000, has_images=True).quality
        assert r_img > r_no_img

    def test_score_quality_code_bonus(self, scorer: ContentScorer) -> None:
        r_no_code = scorer.score(word_count=1000, has_code=False).quality
        r_code = scorer.score(word_count=1000, has_code=True).quality
        assert r_code > r_no_code

    def test_score_quality_zero_word_count(self, scorer: ContentScorer) -> None:
        result = scorer.score(word_count=0)
        assert result.quality == 0.0

    # ── _score_authority() ───────────────────────────────────────

    def test_score_authority_verified_bonus(self, scorer: ContentScorer) -> None:
        r_unverified = scorer.score(
            domain_authority=0.8, is_verified_source=False,
        ).authority
        r_verified = scorer.score(
            domain_authority=0.8, is_verified_source=True,
        ).authority
        assert r_verified > r_unverified

    def test_score_authority_capped_at_one(self, scorer: ContentScorer) -> None:
        result = scorer.score(
            domain_authority=0.95, is_verified_source=True,
        )
        assert result.authority <= 1.0

    def test_score_authority_default(self, scorer: ContentScorer) -> None:
        result = scorer.score()
        assert result.authority == 0.5

    def test_score_authority_verified_bonus_exact(self, scorer: ContentScorer) -> None:
        # Pin the corrected docstring claim: verified adds +0.1 capped at 1.0,
        # unverified returns domain_authority unchanged.
        verified = scorer.score(
            domain_authority=0.9, is_verified_source=True,
        ).authority
        unverified = scorer.score(
            domain_authority=0.9, is_verified_source=False,
        ).authority
        assert verified == 1.0  # 0.9 + 0.1 capped at 1.0
        assert unverified == 0.9  # unchanged

    # ── _score_freshness() ───────────────────────────────────────

    def test_score_freshness_recent_crawl(self, scorer: ContentScorer) -> None:
        now = datetime.now(tz=timezone.utc)
        result = scorer.score(
            last_crawled=now, change_frequency="daily",
        )
        assert result.freshness > 0.9

    def test_score_freshness_stale_crawl(self, scorer: ContentScorer) -> None:
        old = datetime.now(tz=timezone.utc) - timedelta(days=100)
        result = scorer.score(
            last_crawled=old, change_frequency="daily",
        )
        assert result.freshness < 0.5

    def test_score_freshness_never_frequency(self, scorer: ContentScorer) -> None:
        result = scorer.score(
            last_crawled=datetime.now(tz=timezone.utc),
            change_frequency="never",
        )
        assert result.freshness == 1.0

    def test_score_freshness_no_last_crawled(self, scorer: ContentScorer) -> None:
        result = scorer.score()
        assert result.freshness == 0.5

    def test_score_freshness_naive_datetime(self, scorer: ContentScorer) -> None:
        naive = datetime.now()  # noqa: DTZ005
        result = scorer.score(
            last_crawled=naive, change_frequency="daily",
        )
        assert 0.0 <= result.freshness <= 1.0

    # ── rank() ───────────────────────────────────────────────────

    def test_rank_sorted_by_score_desc(self, scorer: ContentScorer) -> None:
        items = [
            {"keyword_matches": 10, "total_keywords": 10},
            {"keyword_matches": 0, "total_keywords": 10},
            {"keyword_matches": 5, "total_keywords": 10},
        ]
        ranked = scorer.rank(items)
        assert len(ranked) == 3
        assert ranked[0][1].total >= ranked[1][1].total
        assert ranked[1][1].total >= ranked[2][1].total

    def test_rank_limit_applied(self, scorer: ContentScorer) -> None:
        items = [
            {"keyword_matches": i, "total_keywords": 10}
            for i in range(20)
        ]
        ranked = scorer.rank(items, limit=5)
        assert len(ranked) == 5

    def test_rank_returns_tuples(self, scorer: ContentScorer) -> None:
        items = [{"keyword_matches": 5, "total_keywords": 10}]
        ranked = scorer.rank(items)
        assert len(ranked) == 1
        item, score = ranked[0]
        assert item["keyword_matches"] == 5
        assert isinstance(score, ContentScore)

    def test_rank_empty_items(self, scorer: ContentScorer) -> None:
        ranked = scorer.rank([])
        assert ranked == []
