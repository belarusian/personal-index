"""Adversarial deep tests for personal_index.content_priority (cycle 216 PROBE).

Never-probed subsystem. Attacks the documented boundary contracts:

* ``PriorityLevel.from_score`` — fixed hardcoded bands (0.8/0.6/0.4/0).
* ``PriorityCalculator.calculate`` — four sub-factors, each documented to be
  in the 0-1 range, weighted total documented to be in [0,1] when the config
  weights sum to 1.0.
* ``_recency_score`` — documented "0-1, higher = more recent".
* ``_engagement_score`` — documented "0.0 when view_count <= 0".
* ``_interest_score`` — documented "capped at 1.0".
* ``get_summary`` — documented to omit absent levels and return {} for empty.

DEFECT (QA-36): ``_recency_score`` is a bare ``math.exp(-days/30.0)`` with no
floor on ``days_since_indexed``. A NEGATIVE ``days_since_indexed`` (a future
date, plausible from upstream date-math bugs) makes the recency sub-factor
EXCEED 1.0 (e^30/30 = 2.718 at day -30), violating the documented "0-1"
range, and consequently pushes the weighted total above 1.0 (1.0437 with
default weights that sum to 1.0), violating the documented "[0,1] when the
config weights sum to 1.0" guarantee. The sibling sub-factors all clamp
(``content_score`` -> min/max to [0,1]; ``engagement`` -> 0.0 for <=0 and
min(1.0, ...); ``interest`` -> min(1.0, ...)). Recency is the ONLY
unguarded sub-factor. Pinned xfail-strict below; the implementer must clamp
``days_since_indexed`` to >= 0 (or clamp the recency score to [0,1]).
"""

from __future__ import annotations


import pytest

from personal_index.content_priority import (
    PriorityCalculator,
    PriorityConfig,
    PriorityLevel,
)


# ---------------------------------------------------------------------------
# DEFECT PINS — QA-36: _recency_score unguarded on negative days_since_indexed
# ---------------------------------------------------------------------------
class TestRecencyNegativeDaysDefect:
    """QA-36: negative days_since_indexed breaks the documented 0-1 range."""

    def test_recency_score_negative_days_exceeds_one(self):
        """_recency_score docstring: '0-1, higher = more recent'.

        day -30 -> e^(30/30) = e = 2.718 > 1.0, violating the 0-1 contract.
        """
        calc = PriorityCalculator()
        score = calc._recency_score(-30.0)
        # Documented contract: recency is in [0, 1] for any input.
        assert 0.0 <= score <= 1.0, (
            f"_recency_score(-30.0) = {score} violates the documented 0-1 "
            f"range (QA-36)"
        )

    def test_calculate_negative_days_total_exceeds_one(self):
        """calculate docstring + docs/content-priority.md: the weighted total
        is 'only guaranteed to be in [0, 1] when the config weights sum to
        1.0'. Default weights sum to exactly 1.0, yet a negative
        days_since_indexed pushes the total above 1.0.
        """
        calc = PriorityCalculator()  # default weights sum to 1.0
        result = calc.calculate(
            "u", "t",
            content_score=10.0,
            view_count=100,
            days_since_indexed=-30.0,
        )
        assert 0.0 <= result.score <= 1.0, (
            f"calculate(..., days_since_indexed=-30.0).score = {result.score} "
            f"exceeds the documented [0, 1] total range (QA-36)"
        )


# ---------------------------------------------------------------------------
# CLEAN ARMOR — documented contracts that hold (regression guards)
# ---------------------------------------------------------------------------
class TestFromScoreBands:
    """PriorityLevel.from_score — fixed hardcoded bands, inclusive >=."""

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0.8, PriorityLevel.CRITICAL),
            (0.7999, PriorityLevel.HIGH),
            (0.6, PriorityLevel.HIGH),
            (0.5999, PriorityLevel.MEDIUM),
            (0.4, PriorityLevel.MEDIUM),
            (0.3999, PriorityLevel.LOW),
            (0.0, PriorityLevel.ARCHIVE),
            (0.1, PriorityLevel.LOW),
            (-0.5, PriorityLevel.ARCHIVE),
            (1.0, PriorityLevel.CRITICAL),
            (2.0, PriorityLevel.CRITICAL),
        ],
    )
    def test_bands(self, score, expected):
        assert PriorityLevel.from_score(score) is expected

    def test_from_score_ignores_config(self):
        """from_score is standalone: it does NOT read PriorityConfig."""
        # Even with a config that would map 0.5 -> CRITICAL, from_score(0.5)
        # still returns MEDIUM (fixed bands).
        assert PriorityLevel.from_score(0.5) is PriorityLevel.MEDIUM


class TestSubFactorRanges:
    """Each sub-factor is documented to be in [0, 1]."""

    def test_content_score_clamped(self):
        calc = PriorityCalculator()
        r = calc.calculate("u", "t", content_score=-50.0, days_since_indexed=0.0)
        assert r.breakdown["content_score"] == 0.0
        r2 = calc.calculate("u", "t", content_score=50.0, days_since_indexed=0.0)
        assert r2.breakdown["content_score"] == 1.0

    def test_engagement_negative_and_zero(self):
        calc = PriorityCalculator()
        assert calc._engagement_score(-100) == 0.0
        assert calc._engagement_score(0) == 0.0

    def test_engagement_saturates_at_100(self):
        calc = PriorityCalculator()
        assert calc._engagement_score(100) == 1.0
        assert calc._engagement_score(1000) == 1.0

    def test_interest_capped_at_one(self):
        calc = PriorityCalculator()
        assert calc._interest_score([]) == 0.0
        assert calc._interest_score(["a", "b", "c", "d"]) == 1.0
        assert calc._interest_score(["a"] * 10) == 1.0

    def test_recency_positive_days_in_range(self):
        """Positive days_since_indexed stays in [0, 1] (the guarded half)."""
        calc = PriorityCalculator()
        for days in (0.0, 1.0, 30.0, 100.0, 1000.0):
            assert 0.0 <= calc._recency_score(days) <= 1.0


class TestLevelForScoreBoundaries:
    """_level_for_score — config-driven, all boundaries inclusive (>=)."""

    def test_default_boundaries(self):
        calc = PriorityCalculator()
        assert calc._level_for_score(0.8) is PriorityLevel.CRITICAL
        assert calc._level_for_score(0.6) is PriorityLevel.HIGH
        assert calc._level_for_score(0.4) is PriorityLevel.MEDIUM
        assert calc._level_for_score(0.2) is PriorityLevel.LOW
        assert calc._level_for_score(0.1999) is PriorityLevel.ARCHIVE

    def test_config_thresholds_respected(self):
        cfg = PriorityConfig(
            critical_threshold=0.95, high_threshold=0.9,
            medium_threshold=0.7, low_threshold=0.5,
        )
        calc = PriorityCalculator(config=cfg)
        assert calc._level_for_score(0.5) is PriorityLevel.LOW
        assert calc._level_for_score(0.7) is PriorityLevel.MEDIUM
        assert calc._level_for_score(0.9) is PriorityLevel.HIGH


class TestSummaryAndBatch:
    """get_summary omits absent levels; batch_calculate tolerates missing keys."""

    def test_summary_empty(self):
        calc = PriorityCalculator()
        assert calc.get_summary([]) == {}

    def test_summary_omits_absent_levels(self):
        calc = PriorityCalculator()
        results = [
            calc.calculate(
                "a", "a", content_score=10.0,
                interest_matches=["x", "y", "z", "w"],
                view_count=100, days_since_indexed=0.0,
            ),
            calc.calculate(
                "b", "b", content_score=10.0,
                interest_matches=["x", "y", "z", "w"],
                view_count=100, days_since_indexed=0.0,
            ),
        ]
        summary = calc.get_summary(results)
        assert summary == {"critical": 2}
        assert "low" not in summary
        assert "archive" not in summary

    def test_batch_missing_keys_defaults(self):
        calc = PriorityCalculator()
        results = calc.batch_calculate([{}])
        assert results[0].url == ""
        assert results[0].title == ""

    def test_batch_sorted_descending(self):
        calc = PriorityCalculator()
        items = [
            {"url": "low", "title": "low", "content_score": 1.0, "days_since_indexed": 100.0},
            {"url": "high", "title": "high", "content_score": 10.0, "days_since_indexed": 0.0},
        ]
        results = calc.batch_calculate(items)
        assert results[0].url == "high"
        assert results[0].score >= results[1].score
