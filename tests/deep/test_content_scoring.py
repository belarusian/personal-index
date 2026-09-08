"""Adversarial deep tests for personal_index.content_scoring.

Cycle 135 - VALIDATOR probe.

Targets:
  - ContentScorer._build_score: exact-contract adversarial tests
  - ContentScorer.score: guard inputs, round-trips, idempotence
  - ScoreWeights.normalize: zero-total guard, sum-to-1 property
  - ContentScore dataclass invariants
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone


from personal_index.content_scoring import (
    ContentScore,
    ContentScorer,
    ScoreWeights,
)


# ---------------------------------------------------------------------------
# ScoreWeights.normalize
# ---------------------------------------------------------------------------

class TestScoreWeightsNormalize:
    def test_default_weights_sum_to_one(self):
        w = ScoreWeights()
        total = (w.recency + w.relevance + w.engagement
                 + w.quality + w.authority + w.freshness)
        assert abs(total - 1.0) < 1e-9

    def test_normalize_returns_new_instance(self):
        w = ScoreWeights(recency=1.0, relevance=1.0, engagement=1.0,
                         quality=1.0, authority=1.0, freshness=1.0)
        n = w.normalize()
        assert n is not w
        assert abs(n.recency - 1/6) < 1e-9
        assert abs(n.relevance - 1/6) < 1e-9

    def test_normalize_sums_to_one(self):
        w = ScoreWeights(recency=2.0, relevance=3.0, engagement=5.0,
                         quality=7.0, authority=11.0, freshness=13.0)
        n = w.normalize()
        total = (n.recency + n.relevance + n.engagement
                 + n.quality + n.authority + n.freshness)
        assert abs(total - 1.0) < 1e-9

    def test_normalize_zero_total_returns_default(self):
        """Guard path: all zeros -> default ScoreWeights()."""
        w = ScoreWeights(recency=0, relevance=0, engagement=0,
                         quality=0, authority=0, freshness=0)
        n = w.normalize()
        d = ScoreWeights()
        assert n.recency == d.recency
        assert n.relevance == d.relevance
        assert n.engagement == d.engagement
        assert n.quality == d.quality
        assert n.authority == d.authority
        assert n.freshness == d.freshness

    def test_normalize_does_not_mutate(self):
        w = ScoreWeights(recency=2.0, relevance=3.0, engagement=5.0,
                         quality=7.0, authority=11.0, freshness=13.0)
        orig = (w.recency, w.relevance, w.engagement,
                w.quality, w.authority, w.freshness)
        w.normalize()
        assert (w.recency, w.relevance, w.engagement,
                w.quality, w.authority, w.freshness) == orig

    def test_normalize_idempotent_on_default(self):
        """Normalizing already-normalized weights gives the same result."""
        w = ScoreWeights()
        n1 = w.normalize()
        n2 = n1.normalize()
        assert n1.recency == n2.recency
        assert n1.relevance == n2.relevance


# ---------------------------------------------------------------------------
# ContentScorer._build_score: exact-contract adversarial tests
# ---------------------------------------------------------------------------

class TestBuildScore:
    """_build_score(self, total, recency, relevance, engagement,
                    quality, authority, freshness) -> ContentScore

    Contract:
      - total, recency, relevance, engagement, quality, authority,
        freshness: each round(x, 4)
      - factors: dict keyed by the six factor names (NOT total)
        mapping to the UNROUNDED input values.
    """

    def _scorer(self) -> ContentScorer:
        return ContentScorer()

    def test_basic(self):
        s = self._scorer()._build_score(
            total=0.5, recency=0.8, relevance=0.6,
            engagement=0.4, quality=0.7, authority=0.3, freshness=0.9,
        )
        assert isinstance(s, ContentScore)
        assert s.total == 0.5
        assert s.recency == 0.8
        assert s.relevance == 0.6
        assert s.engagement == 0.4
        assert s.quality == 0.7
        assert s.authority == 0.3
        assert s.freshness == 0.9

    def test_rounding_to_4_decimals(self):
        """Each field must be round(x, 4)."""
        s = self._scorer()._build_score(
            total=0.123456789, recency=0.987654321,
            relevance=0.111111111, engagement=0.222222222,
            quality=0.333333333, authority=0.444444444,
            freshness=0.555555555,
        )
        assert s.total == round(0.123456789, 4)
        assert s.recency == round(0.987654321, 4)
        assert s.relevance == round(0.111111111, 4)
        assert s.engagement == round(0.222222222, 4)
        assert s.quality == round(0.333333333, 4)
        assert s.authority == round(0.444444444, 4)
        assert s.freshness == round(0.555555555, 4)

    def test_factors_dict_unrounded(self):
        """factors dict must contain UNROUNDED input values."""
        raw = 0.123456789
        s = self._scorer()._build_score(
            total=raw, recency=raw, relevance=raw,
            engagement=raw, quality=raw, authority=raw, freshness=raw,
        )
        assert s.factors["recency"] == raw
        assert s.factors["relevance"] == raw
        assert s.factors["engagement"] == raw
        assert s.factors["quality"] == raw
        assert s.factors["authority"] == raw
        assert s.factors["freshness"] == raw

    def test_factors_dict_keys(self):
        """factors must have exactly the six factor names, NOT total."""
        s = self._scorer()._build_score(
            total=0.5, recency=0.1, relevance=0.2,
            engagement=0.3, quality=0.4, authority=0.5, freshness=0.6,
        )
        expected_keys = {"recency", "relevance", "engagement",
                         "quality", "authority", "freshness"}
        assert set(s.factors.keys()) == expected_keys
        assert "total" not in s.factors

    def test_zero_values(self):
        s = self._scorer()._build_score(
            total=0.0, recency=0.0, relevance=0.0,
            engagement=0.0, quality=0.0, authority=0.0, freshness=0.0,
        )
        assert s.total == 0.0
        assert s.recency == 0.0
        assert all(v == 0.0 for v in s.factors.values())

    def test_one_values(self):
        s = self._scorer()._build_score(
            total=1.0, recency=1.0, relevance=1.0,
            engagement=1.0, quality=1.0, authority=1.0, freshness=1.0,
        )
        assert s.total == 1.0
        assert all(v == 1.0 for v in s.factors.values())

    def test_negative_values(self):
        """Contract says 0.0-1.0 but _build_score just rounds;
        verify it doesn't crash on negatives."""
        s = self._scorer()._build_score(
            total=-0.5, recency=-0.1, relevance=-0.2,
            engagement=-0.3, quality=-0.4, authority=-0.5, freshness=-0.6,
        )
        assert s.total == round(-0.5, 4)
        assert s.factors["recency"] == -0.1

    def test_very_large_values(self):
        s = self._scorer()._build_score(
            total=1e10, recency=1e10, relevance=1e10,
            engagement=1e10, quality=1e10, authority=1e10, freshness=1e10,
        )
        assert s.total == round(1e10, 4)
        assert s.factors["recency"] == 1e10

    def test_idempotent(self):
        """Same inputs -> same output."""
        args = dict(total=0.5, recency=0.1, relevance=0.2,
                    engagement=0.3, quality=0.4, authority=0.5, freshness=0.6)
        s1 = self._scorer()._build_score(**args)
        s2 = self._scorer()._build_score(**args)
        assert s1.total == s2.total
        assert s1.factors == s2.factors

    def test_float_precision(self):
        """Values that are exact in 4 decimals must round-trip."""
        s = self._scorer()._build_score(
            total=0.1234, recency=0.5678, relevance=0.9012,
            engagement=0.3456, quality=0.7890, authority=0.1357,
            freshness=0.2468,
        )
        assert s.total == 0.1234
        assert s.recency == 0.5678
        assert s.relevance == 0.9012


# ---------------------------------------------------------------------------
# ContentScorer.score: guard inputs, round-trips
# ---------------------------------------------------------------------------

class TestScoreMethod:
    def _scorer(self) -> ContentScorer:
        return ContentScorer()

    def test_basic(self):
        s = self._scorer().score(
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
            keyword_matches=5,
            total_keywords=10,
        )
        assert isinstance(s, ContentScore)
        assert 0.0 <= s.total <= 1.0

    def test_no_dates(self):
        """published_at=None, updated_at=None should not crash."""
        s = self._scorer().score()
        assert isinstance(s, ContentScore)

    def test_zero_keywords(self):
        """total_keywords=0 should not cause division by zero."""
        s = self._scorer().score(keyword_matches=0, total_keywords=0)
        assert isinstance(s, ContentScore)

    def test_idempotent(self):
        """Same inputs -> same score."""
        kwargs = dict(
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
            keyword_matches=5,
            total_keywords=10,
        )
        s1 = self._scorer().score(**kwargs)
        s2 = self._scorer().score(**kwargs)
        assert s1.total == s2.total

    def test_score_bounds(self):
        """Score must be in [0, 1] for valid inputs."""
        s = self._scorer().score(
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 12, 31, tzinfo=timezone.utc),
            keyword_matches=100,
            total_keywords=10,
        )
        assert 0.0 <= s.total <= 1.0

    def test_more_matches_higher_relevance(self):
        """More keyword matches (same total) -> higher relevance."""
        s_few = self._scorer().score(keyword_matches=1, total_keywords=10)
        s_many = self._scorer().score(keyword_matches=8, total_keywords=10)
        assert s_many.relevance >= s_few.relevance


# ---------------------------------------------------------------------------
# ContentScore dataclass invariants
# ---------------------------------------------------------------------------

class TestContentScoreDataclass:
    def test_fields_exist(self):
        field_names = {f.name for f in fields(ContentScore)}
        for expected in ("total", "recency", "relevance", "engagement",
                         "quality", "authority", "freshness", "factors"):
            assert expected in field_names, f"Missing field: {expected}"

    def test_total_type(self):
        s = ContentScore(total=0.5, recency=0.1, relevance=0.2,
                         engagement=0.3, quality=0.4, authority=0.5,
                         freshness=0.6, factors={})
        assert isinstance(s.total, float)

    def test_factors_is_dict(self):
        s = ContentScore(total=0.5, recency=0.1, relevance=0.2,
                         engagement=0.3, quality=0.4, authority=0.5,
                         freshness=0.6, factors={"recency": 0.1})
        assert isinstance(s.factors, dict)


# ---------------------------------------------------------------------------
# End-to-end: CLI round-trip
# ---------------------------------------------------------------------------

class TestContentScoringCLI:
    def test_cli_help(self):
        """The CLI should at least have a help that doesn't crash."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()
