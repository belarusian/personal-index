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

import sys
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Cycle 364 PROBE — additional adversarial pins for the documented contracts
# not yet covered by the cycle-216 file (factor thresholds, first-3 truncation,
# to_dict shape, idempotence, custom-weight total, batch empty, CLI e2e).
# ---------------------------------------------------------------------------
class TestFactorThresholds:
    """Each sub-factor is added to ``factors`` only when STRICTLY > 0.7
    (the documented ``_add_factor`` threshold), and the engagement factor
    fires only when ``view_count > 10`` (strict)."""

    def test_content_score_factor_strict_seven(self):
        calc = PriorityCalculator()
        # content_score 7.0 -> 0.7 (NOT > 0.7) -> no factor; 7.01 -> 0.701 -> factor.
        r7 = calc.calculate("u", "t", content_score=7.0, days_since_indexed=0.0)
        r701 = calc.calculate("u", "t", content_score=7.01, days_since_indexed=0.0)
        assert not any("high content" in f for f in r7.factors)
        assert any("high content" in f for f in r701.factors)

    def test_engagement_factor_strict_eleven(self):
        calc = PriorityCalculator()
        r10 = calc.calculate("u", "t", view_count=10, days_since_indexed=0.0)
        r11 = calc.calculate("u", "t", view_count=11, days_since_indexed=0.0)
        assert not any("high engagement" in f for f in r10.factors)
        assert any("high engagement (11 views)" in f for f in r11.factors)

    def test_recency_factor_strict_seven(self):
        calc = PriorityCalculator()
        # e^(-10/30) = 0.7165 (> 0.7 -> factor); e^(-11/30) = 0.693 (<= 0.7 -> none).
        r10 = calc.calculate("u", "t", days_since_indexed=10.0)
        r11 = calc.calculate("u", "t", days_since_indexed=11.0)
        assert any("recently indexed" in f for f in r10.factors)
        assert not any("recently indexed" in f for f in r11.factors)


class TestInterestFactorTruncation:
    """The interest factor lists only the FIRST 3 matches (documented
    ``interest_matches[:3]``), even when more are supplied."""

    def test_interest_factor_truncates_to_first_three(self):
        calc = PriorityCalculator()
        r = calc.calculate(
            "u", "t", interest_matches=["a", "b", "c", "d", "e"],
            days_since_indexed=0.0,
        )
        interest_factors = [f for f in r.factors if "interests" in f]
        assert interest_factors == ["matches interests: a, b, c"]
        # The score still reflects ALL 5 matches (capped at 1.0), not just 3.
        assert r.breakdown["interest_match"] == 1.0


class TestToDictShape:
    """PriorityResult.to_dict() — exact key set, priority serialized to its
    string value, score/breakdown rounded to 4 places."""

    def test_to_dict_exact_keys_and_priority_value(self):
        calc = PriorityCalculator()
        r = calc.calculate(
            "https://x.com/a", "Title", content_score=10.0,
            interest_matches=["a", "b", "c", "d"], view_count=100,
            days_since_indexed=0.0,
        )
        d = r.to_dict()
        assert set(d.keys()) == {"url", "title", "priority", "score", "breakdown", "factors"}
        assert d["priority"] == "critical"          # serialized to .value (str)
        assert isinstance(d["priority"], str)
        assert d["url"] == "https://x.com/a"
        assert d["title"] == "Title"
        # score is the weighted total, rounded to 4 places.
        assert d["score"] == round(r.score, 4)
        # breakdown keys are the four documented sub-factors.
        assert set(d["breakdown"].keys()) == {"recency", "content_score", "interest_match", "engagement"}


class TestIdempotenceAndWeights:
    """calculate() is a pure function of its inputs (idempotent), and the
    weighted total is bounded by the config weights (sum 1.0 -> total in [0,1])."""

    def test_calculate_is_idempotent(self):
        calc = PriorityCalculator()
        a = calc.calculate("u", "t", content_score=5.0, interest_matches=["x"],
                           view_count=20, days_since_indexed=3.0)
        b = calc.calculate("u", "t", content_score=5.0, interest_matches=["x"],
                           view_count=20, days_since_indexed=3.0)
        assert a.score == b.score
        assert a.priority is b.priority
        assert a.breakdown == b.breakdown
        assert a.factors == b.factors

    def test_default_weights_total_bounded_one(self):
        """With default weights (sum 1.0) and every sub-factor at its max,
        the weighted total is exactly 1.0 (the documented [0,1] bound)."""
        calc = PriorityCalculator()
        r = calc.calculate(
            "u", "t", content_score=10.0, interest_matches=["a", "b", "c", "d"],
            view_count=100, days_since_indexed=0.0,
        )
        assert r.score == 1.0
        assert r.priority is PriorityLevel.CRITICAL

    def test_custom_weights_total_exceeds_one(self):
        """With weights that sum to 4.0 the total is NOT bounded to [0,1]
        (documented bound holds only when weights sum to 1.0); the level is
        still clamped to CRITICAL by the threshold."""
        cfg = PriorityConfig(
            recency_weight=1.0, score_weight=1.0,
            interest_weight=1.0, engagement_weight=1.0,
        )
        calc = PriorityCalculator(config=cfg)
        r = calc.calculate(
            "u", "t", content_score=10.0, interest_matches=["a", "b", "c", "d"],
            view_count=100, days_since_indexed=0.0,
        )
        assert r.score == 4.0
        assert r.priority is PriorityLevel.CRITICAL


class TestBatchAndSummaryEdge:
    """batch_calculate([]) -> [] and get_summary over a single result."""

    def test_batch_empty_returns_empty(self):
        calc = PriorityCalculator()
        assert calc.batch_calculate([]) == []

    def test_summary_single_result(self):
        calc = PriorityCalculator()
        # All sub-factors maxed -> weighted total 1.0 -> CRITICAL.
        r = calc.calculate(
            "u", "t", content_score=10.0, interest_matches=["a", "b", "c", "d"],
            view_count=100, days_since_indexed=0.0,
        )
        assert r.priority is PriorityLevel.CRITICAL
        assert calc.get_summary([r]) == {"critical": 1}


class TestCliEndToEnd:
    """One end-to-end run through the installed CLI entry point (init + stats)
    to confirm the installed package runs without error on a fresh data dir."""

    def test_cli_init_and_stats(self, tmp_path):
        import subprocess
        data_dir = tmp_path / "cli_data"
        init = subprocess.run(
            [sys.executable, "-m", "personal_index", "init", "--data-dir", str(data_dir)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
        )
        assert init.returncode == 0, f"init failed: {init.stderr}"
        stats = subprocess.run(
            [sys.executable, "-m", "personal_index", "stats", "--data-dir", str(data_dir)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
        )
        assert stats.returncode == 0, f"stats failed: {stats.stderr}"
        assert "indexed_pages" in stats.stdout
