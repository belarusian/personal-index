"""Tests for content priority scoring module."""

from __future__ import annotations

from personal_index.content_priority import (
    PriorityCalculator,
    PriorityConfig,
    PriorityLevel,
    PriorityResult,
)


class TestPriorityResult:
    def test_to_dict(self):
        result = PriorityResult(
            url="https://x.com",
            title="Test",
            priority=PriorityLevel.HIGH,
            score=0.75,
            breakdown={"recency": 0.8},
            factors=["recently indexed"],
        )
        d = result.to_dict()
        assert d["priority"] == "high"
        assert d["score"] == 0.75
        assert "recency" in d["breakdown"]


class TestPriorityCalculator:
    def test_high_priority_item(self):
        calc = PriorityCalculator()
        result = calc.calculate(
            url="https://example.com",
            title="Important Article",
            content_score=9.0,
            interest_matches=["python", "programming"],
            view_count=50,
            days_since_indexed=1.0,
        )
        assert result.priority in (PriorityLevel.CRITICAL, PriorityLevel.HIGH)
        assert result.score > 0.5

    def test_low_priority_item(self):
        calc = PriorityCalculator()
        result = calc.calculate(
            url="https://example.com",
            title="Old Content",
            content_score=1.0,
            interest_matches=[],
            view_count=0,
            days_since_indexed=365.0,
        )
        assert result.priority in (PriorityLevel.LOW, PriorityLevel.ARCHIVE)
        assert result.score < 0.3

    def test_recency_decay(self):
        calc = PriorityCalculator()
        recent = calc.calculate(
            url="https://a.com", title="Recent",
            days_since_indexed=1.0,
        )
        old = calc.calculate(
            url="https://b.com", title="Old",
            days_since_indexed=90.0,
        )
        assert recent.breakdown["recency"] > old.breakdown["recency"]

    def test_interest_matching(self):
        calc = PriorityCalculator()
        with_match = calc.calculate(
            url="https://a.com", title="Match",
            interest_matches=["python", "web", "dev", "code"],
        )
        no_match = calc.calculate(
            url="https://b.com", title="No Match",
            interest_matches=[],
        )
        assert with_match.breakdown["interest_match"] > no_match.breakdown["interest_match"]

    def test_engagement_scaling(self):
        calc = PriorityCalculator()
        high_views = calc.calculate(
            url="https://a.com", title="Popular",
            view_count=100,
        )
        low_views = calc.calculate(
            url="https://b.com", title="Unpopular",
            view_count=1,
        )
        assert high_views.breakdown["engagement"] > low_views.breakdown["engagement"]

    def test_engagement_score_stays_in_0_1_range(self):
        """Regression: _engagement_score must stay within the documented 0-1 range.

        TICKET-305: the body previously returned log(1+views)/log(101) uncapped,
        exceeding 1.0 for view_count > 100. It must saturate at 1.0.
        """
        calc = PriorityCalculator()
        for view_count in [0, 1, 10, 100, 101, 1000, 10000]:
            score = calc._engagement_score(view_count)
            assert 0.0 <= score <= 1.0, (
                f"engagement score {score} out of [0,1] for view_count={view_count}"
            )
        # Saturates at 1.0 for 100+ views (the log(101) normalization point).
        assert calc._engagement_score(100) == 1.0
        assert calc._engagement_score(101) == 1.0
        assert calc._engagement_score(10000) == 1.0
        # Non-decreasing in view_count.
        scores = [calc._engagement_score(v) for v in [0, 1, 10, 100, 101, 1000, 10000]]
        assert scores == sorted(scores)

    def test_total_score_stays_in_0_1_range(self):
        """Regression: a very popular item's total score must stay within [0,1].

        TICKET-305: uncapped engagement pushed the weighted total above 1.0
        (weights sum to 1.0, so every factor in [0,1] keeps the total in [0,1]).
        """
        calc = PriorityCalculator()
        result = calc.calculate(
            url="https://a.com",
            title="Hot",
            content_score=10.0,
            interest_matches=["a", "b", "c", "d"],
            view_count=10000,
            days_since_indexed=0.0,
        )
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.breakdown["engagement"] <= 1.0

    def test_batch_calculate(self):
        calc = PriorityCalculator()
        results = calc.batch_calculate([
            {"url": "https://a.com", "title": "A", "content_score": 9.0, "interest_matches": ["python"]},
            {"url": "https://b.com", "title": "B", "content_score": 1.0},
            {"url": "https://c.com", "title": "C", "content_score": 5.0, "interest_matches": ["web"]},
        ])
        assert len(results) == 3
        # Should be sorted by score descending
        assert results[0].score >= results[1].score >= results[2].score

    def test_get_summary(self):
        calc = PriorityCalculator()
        results = calc.batch_calculate([
            {"url": "https://a.com", "title": "A", "content_score": 9.0, "interest_matches": ["python"]},
            {"url": "https://b.com", "title": "B", "content_score": 1.0},
            {"url": "https://c.com", "title": "C", "content_score": 5.0},
        ])
        summary = calc.get_summary(results)
        assert sum(summary.values()) == 3

    def test_custom_thresholds(self):
        config = PriorityConfig(
            critical_threshold=0.9,
            high_threshold=0.7,
            medium_threshold=0.5,
            low_threshold=0.3,
        )
        calc = PriorityCalculator(config=config)
        result = calc.calculate(
            url="https://x.com", title="Test",
            content_score=8.0,
            interest_matches=["python"],
            view_count=20,
            days_since_indexed=5.0,
        )
        assert result.priority in PriorityLevel

    def test_factors_populated(self):
        calc = PriorityCalculator()
        result = calc.calculate(
            url="https://x.com", title="Test",
            content_score=9.0,
            interest_matches=["python"],
            view_count=50,
            days_since_indexed=1.0,
        )
        assert len(result.factors) > 0
        assert "recently indexed" in result.factors

    def test_zero_values(self):
        calc = PriorityCalculator()
        result = calc.calculate(
            url="https://x.com", title="Test",
        )
        assert result.score >= 0
        assert result.priority in PriorityLevel
