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


class TestScoreWeightsNormalizePinning:
    """Pinning tests for ScoreWeights.normalize returned-object fields."""

    def test_normalize_returns_new_instance_and_divides_by_total(self) -> None:
        w = ScoreWeights(
            recency=0.5, relevance=0.5,
            engagement=0.0, quality=0.0, authority=0.0, freshness=0.0,
        )
        n = w.normalize()
        # returned object is a NEW instance, not the original
        assert n is not w
        # each field == weight / total (total == 1.0 here)
        assert abs(n.recency - 0.5) < 0.001
        assert abs(n.relevance - 0.5) < 0.001
        assert n.engagement == 0.0
        assert n.quality == 0.0
        assert n.authority == 0.0
        assert n.freshness == 0.0
        total = (
            n.recency + n.relevance + n.engagement
            + n.quality + n.authority + n.freshness
        )
        assert abs(total - 1.0) < 0.001
        # original instance is NOT mutated
        assert w.recency == 0.5
        assert w.relevance == 0.5
        assert w.engagement == 0.0

    def test_normalize_all_zero_guard_returns_default_fields(self) -> None:
        w = ScoreWeights(
            recency=0, relevance=0, engagement=0,
            quality=0, authority=0, freshness=0,
        )
        n = w.normalize()
        # guard path: total == 0 -> DEFAULT ScoreWeights() fields, no ZeroDivisionError
        assert n is not w
        assert n.recency == 0.2
        assert n.relevance == 0.25
        assert n.engagement == 0.15
        assert n.quality == 0.15
        assert n.authority == 0.1
        assert n.freshness == 0.15
        # original all-zero instance is NOT mutated
        assert w.recency == 0
        assert w.relevance == 0


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

    def test_score_relevance_direct_contract(self, scorer: ContentScorer) -> None:
        """Pin the exact _score_relevance contract against the returned float.

        Guard path (total_keywords == 0) -> 0.0; normal path ->
        round(min(1.0, keyword_matches / total_keywords), 4).
        """
        # Guard path: no keywords to match against -> 0.0 (no division by zero).
        assert scorer._score_relevance(0, 0) == 0.0
        # Normal path: exact fraction, rounded to 4 places.
        assert scorer._score_relevance(5, 10) == 0.5
        # Capped at 1.0 when matches exceed the total.
        assert scorer._score_relevance(15, 10) == 1.0
        # Non-terminating fraction rounded to 4 places.
        assert scorer._score_relevance(1, 3) == 0.3333

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

    def test_score_freshness_direct_contract(self, scorer: ContentScorer) -> None:
        # Guard path: last_crawled is None -> neutral 0.5.
        assert scorer._score_freshness(None, "daily", None) == 0.5
        # 'never' frequency short-circuits to 1.0 regardless of age.
        assert scorer._score_freshness(
            datetime.now(tz=timezone.utc), "never", None
        ) == 1.0
        # Decay: just-crawled content (age ~0) scores ~1.0.
        assert scorer._score_freshness(
            datetime.now(tz=timezone.utc), "daily", None
        ) == 1.0
        # Decay clamp: 100 days old at daily (expected 24h) -> ratio 100,
        # 1.0 - 100*0.5 clamps to 0.0.
        old = datetime.now(tz=timezone.utc) - timedelta(days=100)
        assert scorer._score_freshness(old, "daily", None) == 0.0

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

    def test_score_pins_returned_object_fields_normal_and_guard(self, scorer: ContentScorer) -> None:
        # Normal case: pins the returned ContentScore object fields (not counters).
        normal = scorer.score(
            keyword_matches=10, total_keywords=10,
            view_count=100, bookmark_count=10, share_count=5,
            word_count=3000, has_images=True, has_code=True,
            domain_authority=0.9, is_verified_source=True,
        )
        assert isinstance(normal, ContentScore)
        assert normal.relevance == 1.0
        assert normal.authority == 1.0
        assert normal.quality == 1.0
        assert 0.0 < normal.engagement <= 1.0
        assert 0.0 <= normal.recency <= 1.0
        assert 0.0 <= normal.freshness <= 1.0
        # factors dict maps each factor name to its (unrounded) value.
        assert set(normal.factors) == {
            "recency", "relevance", "engagement",
            "quality", "authority", "freshness",
        }
        assert normal.factors["relevance"] == 1.0
        assert normal.factors["authority"] == 1.0
        # total is the weighted sum of the six factors (normalized weights).
        expected_total = (
            scorer.weights.recency * normal.recency
            + scorer.weights.relevance * normal.relevance
            + scorer.weights.engagement * normal.engagement
            + scorer.weights.quality * normal.quality
            + scorer.weights.authority * normal.authority
            + scorer.weights.freshness * normal.freshness
        )
        assert abs(normal.total - round(expected_total, 4)) < 0.001

        # Guard path: no-arg default call pins the guard/early-return fields.
        guard = scorer.score()
        assert isinstance(guard, ContentScore)
        assert guard.relevance == 0.0
        assert guard.engagement == 0.0
        assert guard.quality == 0.0
        assert guard.authority == 0.5
        assert guard.freshness == 0.5
        assert set(guard.factors) == {
            "recency", "relevance", "engagement",
            "quality", "authority", "freshness",
        }
        assert guard.factors["authority"] == 0.5
        assert guard.factors["freshness"] == 0.5


# ── score_page doc-drift pinning (TICKET-430) ──────────────────────

class _FakeInterest:
    def __init__(self, keywords, topics=(), value=""):
        self.keywords = keywords
        self.topics = list(topics)
        self.value = value


class _FakeInterestStore:
    def __init__(self, interests):
        self._interests = interests

    def list_all(self):
        return self._interests


class _FakePage:
    def __init__(self, content, word_count=0, domain_authority=0.5, crawled_at=None):
        self.content = content
        self.word_count = word_count
        self.domain_authority = domain_authority
        self.crawled_at = crawled_at


class TestScorePagePinning:
    """Pin the corrected score_page contract (normal + guard path)."""

    def test_normal_interest_matching(self):
        """Normal case: a matching keyword drives relevance > 0."""
        scorer = ContentScorer()
        store = _FakeInterestStore([
            _FakeInterest(keywords=["python", "django"]),
        ])
        page = _FakePage(content="Learning python and django today")
        score = scorer.score_page(page, interest_store=store)
        assert isinstance(score, ContentScore)
        # 2 candidates (python, django), both match -> relevance 1.0
        assert score.relevance == 1.0
        assert score.factors["relevance"] == 1.0

    def test_guard_path_no_interest_store(self):
        """Guard path: falsy interest_store -> relevance 0.0."""
        scorer = ContentScorer()
        page = _FakePage(content="Learning python and django today")
        score = scorer.score_page(page, interest_store=None)
        assert isinstance(score, ContentScore)
        assert score.relevance == 0.0
        assert score.factors["relevance"] == 0.0


class TestBuildScoreContract:
    """Pin the exact return structure of _build_score."""

    def test_build_score_rounds_fields_and_factors_unrounded(self) -> None:
        scorer = ContentScorer()
        # Use values that will change under round(x, 4)
        total = 0.123456789
        recency = 0.987654321
        relevance = 0.555555555
        engagement = 0.111111111
        quality = 0.333333333
        authority = 0.777777777
        freshness = 0.222222222

        result = scorer._build_score(
            total, recency, relevance, engagement, quality, authority, freshness
        )

        # All 7 fields are rounded to 4 dp
        assert result.total == round(total, 4)
        assert result.recency == round(recency, 4)
        assert result.relevance == round(relevance, 4)
        assert result.engagement == round(engagement, 4)
        assert result.quality == round(quality, 4)
        assert result.authority == round(authority, 4)
        assert result.freshness == round(freshness, 4)

        # factors dict: exactly six keys (NOT total), values are UNROUNDED
        assert set(result.factors.keys()) == {
            "recency", "relevance", "engagement",
            "quality", "authority", "freshness",
        }
        assert "total" not in result.factors
        assert result.factors["recency"] == recency
        assert result.factors["relevance"] == relevance
        assert result.factors["engagement"] == engagement
        assert result.factors["quality"] == quality
        assert result.factors["authority"] == authority
        assert result.factors["freshness"] == freshness
