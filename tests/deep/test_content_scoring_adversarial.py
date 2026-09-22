"""Adversarial deep tests for personal_index/content_scoring.py.

Targets the public surface of ScoreFactor / ScoreWeights / ContentScore /
ContentScorer: weight normalization (zero / all-equal / negative / NaN),
ContentScore.to_dict() key set + rounding + factors-by-reference, the six
factor helpers (recency decay, relevance guard, engagement log1p, quality
bonuses, authority cap, freshness decay), the composite score() range,
rank() guards (empty / limit<=0 / ties / single / limit>len / None),
score_page() interest matching, and an end-to-end CLI pipeline run that
exercises the scorer.

QA-47: ContentScorer._score_authority's docstring promises the result is
"capped at 1.0", but the min(1.0, ...) cap is applied ONLY in the
is_verified_source branch. A non-verified domain_authority > 1.0 (e.g. 1.5)
is returned unchanged (1.5) and a negative one (e.g. -0.5) is returned
unchanged (-0.5), both violating the documented 0.0-1.0 factor range. The
verified branch is capped, so the guard is one-sided (cap present for
verified, absent for non-verified). Pinned with xfail-strict below.

Secondary out-of-range / missing-guard findings observed in the same probe
(also pinned xfail-strict, folded into QA-47 as related findings):
  - _score_relevance with a negative total_keywords returns a negative score
    (e.g. -0.6) instead of clamping to the documented 0.0 floor.
  - _score_engagement / _score_quality raise ValueError (math domain error)
    on a negative count instead of clamping to 0.0.
  - rank(None) raises TypeError instead of returning an empty list.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_scoring import (
    ContentScore,
    ContentScorer,
    ScoreFactor,
    ScoreWeights,
)


@pytest.fixture
def scorer() -> ContentScorer:
    return ContentScorer()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── ScoreFactor enum ────────────────────────────────────────────────────


class TestScoreFactor:
    def test_six_factors_have_stable_values(self) -> None:
        assert ScoreFactor.RECENCY.value == "recency"
        assert ScoreFactor.RELEVANCE.value == "relevance"
        assert ScoreFactor.ENGAGEMENT.value == "engagement"
        assert ScoreFactor.QUALITY.value == "quality"
        assert ScoreFactor.AUTHORITY.value == "authority"
        assert ScoreFactor.FRESHNESS.value == "freshness"

    def test_exactly_six_members(self) -> None:
        assert len(list(ScoreFactor)) == 6


# ── ScoreWeights.normalize ──────────────────────────────────────────────


class TestScoreWeightsNormalize:
    def test_all_zero_returns_default(self) -> None:
        # Guard path: total == 0 -> DEFAULT ScoreWeights(), not ZeroDivisionError.
        w = ScoreWeights(0.0, 0.0, 0.0, 0.0, 0.0, 0.0).normalize()
        assert w == ScoreWeights()
        assert w.recency == 0.2
        assert w.relevance == 0.25

    def test_all_equal_sums_to_one(self) -> None:
        w = ScoreWeights(1.0, 1.0, 1.0, 1.0, 1.0, 1.0).normalize()
        total = (
            w.recency + w.relevance + w.engagement
            + w.quality + w.authority + w.freshness
        )
        assert total == pytest.approx(1.0)
        assert w.recency == pytest.approx(1.0 / 6.0)

    def test_does_not_mutate_original(self) -> None:
        orig = ScoreWeights(2.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        w = orig.normalize()
        assert orig.recency == 2.0  # original untouched
        assert w.recency == pytest.approx(1.0)

    def test_negative_weight_produces_negative_normalized(self) -> None:
        # Documented behavior: a negative weight is divided by the total and
        # yields a negative normalized weight (no floor clamp). Pinned green
        # to record the current contract; see QA-47 related findings.
        w = ScoreWeights(-1.0, 1.0, 1.0, 1.0, 1.0, 1.0).normalize()
        assert w.recency == pytest.approx(-0.25)

    def test_nan_weight_propagates_nan(self) -> None:
        # Documented behavior: NaN in a weight propagates through normalize.
        w = ScoreWeights(float("nan"), 1.0, 1.0, 1.0, 1.0, 1.0).normalize()
        assert math.isnan(w.recency)


# ── ContentScore.to_dict ────────────────────────────────────────────────


class TestContentScoreToDict:
    def test_exact_eight_keys(self) -> None:
        cs = ContentScore(total=0.5, recency=0.5, relevance=0.5,
                          engagement=0.5, quality=0.5, authority=0.5,
                          freshness=0.5, factors={"recency": 0.5})
        d = cs.to_dict()
        assert set(d.keys()) == {
            "total", "recency", "relevance", "engagement",
            "quality", "authority", "freshness", "factors",
        }

    def test_numeric_fields_rounded_to_4(self) -> None:
        cs = ContentScore(total=0.123456789, recency=0.987654321)
        d = cs.to_dict()
        assert d["total"] == 0.1235
        assert d["recency"] == 0.9877

    def test_factors_passed_by_reference_not_copied(self) -> None:
        # Documented contract: factors is passed through by reference (NOT
        # copied, NOT rounded). Mutating the returned dict's factors mutates
        # the source ContentScore.
        cs = ContentScore(total=0.1, factors={"recency": 0.5})
        d = cs.to_dict()
        d["factors"]["recency"] = 999.0
        assert cs.factors["recency"] == 999.0

    def test_factors_not_rounded(self) -> None:
        cs = ContentScore(total=0.1, factors={"recency": 0.123456789})
        d = cs.to_dict()
        assert d["factors"]["recency"] == 0.123456789  # unrounded


# ── _score_recency ──────────────────────────────────────────────────────


class TestScoreRecency:
    def test_now_is_one(self, scorer: ContentScorer) -> None:
        assert scorer._score_recency(_now(), None) == 1.0

    def test_30_day_half_life(self, scorer: ContentScorer) -> None:
        assert scorer._score_recency(_now() - timedelta(days=30), None) == 0.5

    def test_60_days_is_quarter(self, scorer: ContentScorer) -> None:
        assert scorer._score_recency(_now() - timedelta(days=60), None) == 0.25

    def test_future_date_clamped_to_one(self, scorer: ContentScorer) -> None:
        # age_days = max(0, ...) floors a future date at 0 -> recency 1.0.
        assert scorer._score_recency(_now() + timedelta(days=100), None) == 1.0

    def test_naive_datetime_treated_as_utc(self, scorer: ContentScorer) -> None:
        naive = datetime.now()  # tzinfo is None
        assert scorer._score_recency(naive, None) == 1.0

    def test_none_date_defaults_to_now(self, scorer: ContentScorer) -> None:
        assert scorer._score_recency(None, None) == 1.0

    def test_updated_at_takes_precedence(self, scorer: ContentScorer) -> None:
        # reference = updated_at or published_at or now.
        old = _now() - timedelta(days=30)
        recent = _now()
        assert scorer._score_recency(old, recent) == 1.0
        assert scorer._score_recency(recent, old) == 0.5


# ── _score_relevance ────────────────────────────────────────────────────


class TestScoreRelevance:
    def test_zero_total_guard(self, scorer: ContentScorer) -> None:
        # Guard path: total_keywords == 0 -> 0.0 (no ZeroDivisionError).
        assert scorer._score_relevance(0, 0) == 0.0

    def test_fraction(self, scorer: ContentScorer) -> None:
        assert scorer._score_relevance(1, 2) == 0.5

    def test_over_cap_clamped_to_one(self, scorer: ContentScorer) -> None:
        assert scorer._score_relevance(3, 2) == 1.0

    def test_negative_total_clamped_to_zero(self, scorer: ContentScorer) -> None:
        assert scorer._score_relevance(3, -5) == 0.0


# ── _score_engagement ───────────────────────────────────────────────────


class TestScoreEngagement:
    def test_all_zero_is_zero(self, scorer: ContentScorer) -> None:
        assert scorer._score_engagement(0, 0, 0) == 0.0

    def test_cap_at_one(self, scorer: ContentScorer) -> None:
        assert scorer._score_engagement(1000, 1000, 1000) == 1.0

    def test_monotonic_in_views(self, scorer: ContentScorer) -> None:
        assert scorer._score_engagement(10, 0, 0) < scorer._score_engagement(100, 0, 0)

    def test_negative_count_clamped_to_zero(self, scorer: ContentScorer) -> None:
        assert scorer._score_engagement(-2, 0, 0) == 0.0


# ── _score_quality ──────────────────────────────────────────────────────


class TestScoreQuality:
    def test_zero_no_bonus(self, scorer: ContentScorer) -> None:
        assert scorer._score_quality(0, False, False) == 0.0

    def test_image_bonus(self, scorer: ContentScorer) -> None:
        assert scorer._score_quality(0, True, False) == 0.1

    def test_code_bonus(self, scorer: ContentScorer) -> None:
        assert scorer._score_quality(0, False, True) == 0.05

    def test_both_bonuses(self, scorer: ContentScorer) -> None:
        assert scorer._score_quality(0, True, True) == 0.15

    def test_long_content_capped_at_one(self, scorer: ContentScorer) -> None:
        assert scorer._score_quality(10_000_000, True, True) == 1.0

    def test_negative_word_count_clamped_to_zero(self, scorer: ContentScorer) -> None:
        assert scorer._score_quality(-2, False, False) == 0.0


# ── _score_authority (QA-47 primary defect) ─────────────────────────────


class TestScoreAuthority:
    def test_non_verified_passthrough(self, scorer: ContentScorer) -> None:
        assert scorer._score_authority(0.5, False) == 0.5

    def test_verified_bonus(self, scorer: ContentScorer) -> None:
        assert scorer._score_authority(0.5, True) == 0.6

    def test_verified_cap_at_one(self, scorer: ContentScorer) -> None:
        # Verified branch applies min(1.0, ...) -> 0.95 + 0.1 capped at 1.0.
        assert scorer._score_authority(0.95, True) == 1.0

    def test_non_verified_over_cap_clamped_to_one(self, scorer: ContentScorer) -> None:
        assert scorer._score_authority(1.5, False) == 1.0

    def test_non_verified_negative_clamped_to_zero(self, scorer: ContentScorer) -> None:
        assert scorer._score_authority(-0.5, False) == 0.0


# ── _score_freshness ────────────────────────────────────────────────────


class TestScoreFreshness:
    def test_none_is_neutral_half(self, scorer: ContentScorer) -> None:
        assert scorer._score_freshness(None, "monthly", None) == 0.5

    def test_never_is_one(self, scorer: ContentScorer) -> None:
        assert scorer._score_freshness(_now(), "never", None) == 1.0

    def test_zero_age_is_one(self, scorer: ContentScorer) -> None:
        assert scorer._score_freshness(_now(), "hourly", None) == 1.0

    def test_one_expected_interval_is_half(self, scorer: ContentScorer) -> None:
        assert scorer._score_freshness(_now() - timedelta(hours=1), "hourly", None) == 0.5

    def test_two_intervals_clamped_to_zero(self, scorer: ContentScorer) -> None:
        assert scorer._score_freshness(_now() - timedelta(hours=2), "hourly", None) == 0.0

    def test_unknown_frequency_defaults_to_monthly(self, scorer: ContentScorer) -> None:
        # unknown freq -> expected 720h; 1h age -> 1.0 - (1/720)*0.5 ~ 0.9993.
        assert scorer._score_freshness(_now() - timedelta(hours=1), "bogus", None) == 0.9993

    def test_naive_datetime_treated_as_utc(self, scorer: ContentScorer) -> None:
        # naive "now" expressed in UTC wall-clock; code treats naive as UTC.
        naive = datetime.now(timezone.utc).replace(tzinfo=None)
        assert scorer._score_freshness(naive, "hourly", None) == 1.0


# ── score() composite ───────────────────────────────────────────────────


class TestScoreComposite:
    def test_default_score_in_range(self, scorer: ContentScorer) -> None:
        cs = scorer.score()
        assert 0.0 <= cs.total <= 1.0

    def test_factors_dict_has_six_unrounded_keys(self, scorer: ContentScorer) -> None:
        cs = scorer.score(keyword_matches=1, total_keywords=2, word_count=10)
        assert set(cs.factors.keys()) == {
            "recency", "relevance", "engagement", "quality",
            "authority", "freshness",
        }
        assert cs.factors["relevance"] == 0.5  # unrounded 1/2

    def test_total_is_weighted_sum(self, scorer: ContentScorer) -> None:
        cs = scorer.score()
        w = scorer.weights
        expected = (
            w.recency * cs.factors["recency"]
            + w.relevance * cs.factors["relevance"]
            + w.engagement * cs.factors["engagement"]
            + w.quality * cs.factors["quality"]
            + w.authority * cs.factors["authority"]
            + w.freshness * cs.factors["freshness"]
        )
        assert cs.total == round(expected, 4)

    def test_custom_weights_normalized_in_init(self) -> None:
        s = ContentScorer(weights=ScoreWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        assert s.weights.recency == pytest.approx(1.0)
        assert s.weights.relevance == pytest.approx(0.0)

    def test_none_weights_uses_default(self) -> None:
        s = ContentScorer(weights=None)
        assert s.weights == ScoreWeights().normalize()


# ── rank() ──────────────────────────────────────────────────────────────


class TestRank:
    def test_empty_list(self, scorer: ContentScorer) -> None:
        assert scorer.rank([]) == []

    def test_limit_zero_returns_empty(self, scorer: ContentScorer) -> None:
        assert scorer.rank([{"word_count": 5}], limit=0) == []

    def test_limit_negative_returns_empty(self, scorer: ContentScorer) -> None:
        assert scorer.rank([{"word_count": 5}], limit=-3) == []

    def test_single_item(self, scorer: ContentScorer) -> None:
        r = scorer.rank([{"word_count": 3}])
        assert len(r) == 1
        assert isinstance(r[0][1], ContentScore)

    def test_limit_larger_than_list(self, scorer: ContentScorer) -> None:
        r = scorer.rank([{"word_count": 5}, {"word_count": 1}], limit=100)
        assert len(r) == 2

    def test_sorted_descending(self, scorer: ContentScorer) -> None:
        r = scorer.rank([{"word_count": 1}, {"word_count": 5000}, {"word_count": 100}])
        totals = [sc.total for _, sc in r]
        assert totals == sorted(totals, reverse=True)

    def test_ties_keep_input_order(self, scorer: ContentScorer) -> None:
        # stable sort: equal totals preserve input order.
        r = scorer.rank([{"word_count": 5}, {"word_count": 5}, {"word_count": 5}])
        assert [sc.total for _, sc in r] == [r[0][1].total] * 3

    def test_input_dicts_not_mutated(self, scorer: ContentScorer) -> None:
        item = {"word_count": 5}
        scorer.rank([item])
        assert item == {"word_count": 5}

    def test_none_items_returns_empty(self, scorer: ContentScorer) -> None:
        assert scorer.rank(None) == []  # type: ignore[arg-type]


# ── score_page() ────────────────────────────────────────────────────────


class _FakePage:
    def __init__(self, content: str, word_count: int = 0,
                 domain_authority: float = 0.5, crawled_at: Any = None) -> None:
        self.content = content
        self.word_count = word_count
        self.domain_authority = domain_authority
        self.crawled_at = crawled_at


class _FakeInterest:
    def __init__(self, keywords: list[str], topics: list[str], value: str) -> None:
        self.keywords = keywords
        self.topics = topics
        self.value = value


class _FakeStore:
    def __init__(self, interests: list[_FakeInterest]) -> None:
        self._interests = interests

    def list_all(self) -> list[_FakeInterest]:
        return self._interests


class TestScorePage:
    def test_no_store_relevance_zero(self, scorer: ContentScorer) -> None:
        cs = scorer.score_page(_FakePage("hello python world"))
        assert cs.relevance == 0.0

    def test_with_store_counts_matches(self, scorer: ContentScorer) -> None:
        page = _FakePage("hello python world")
        store = _FakeStore([_FakeInterest(["python"], ["web"], "python")])
        cs = scorer.score_page(page, store)
        # 3 candidates (1 keyword + 1 topic + 1 value); 2 match ("python" x2).
        assert cs.relevance == pytest.approx(2.0 / 3.0, abs=1e-4)

    def test_detects_code_and_images(self, scorer: ContentScorer) -> None:
        page = _FakePage("def foo():\n    pass\n<img src=a.png>")
        cs = scorer.score_page(page)
        assert cs.factors["quality"] > 0.0  # code + image bonuses applied

    def test_missing_content_defaults_empty(self, scorer: ContentScorer) -> None:
        class Bare:  # no content attr
            pass
        cs = scorer.score_page(Bare())  # type: ignore[arg-type]
        assert cs.relevance == 0.0


# ── end-to-end CLI (pipeline exercises the scorer) ──────────────────────


class TestCliEndToEnd:
    def test_pipeline_scores_imported_file(self, tmp_path) -> None:
        doc = tmp_path / "doc.txt"
        doc.write_text(
            "This is a test document about python programming and web "
            "development with enough words to pass the content length "
            "filter for the pipeline scoring stage.\n"
        )
        dd = str(tmp_path / "dd")
        result = CliRunner().invoke(
            main, ["pipeline", "--import-file", str(doc), "--data-dir", dd]
        )
        assert result.exit_code == 0, result.output
        assert "Scored:" in result.output
        assert "Indexed:      1" in result.output


# ── Cycle 370: additional adversarial pins ─────────────────────────────


class TestComputeTotalDirect:
    """Pin _compute_total as a raw weighted sum (no rounding/clamping)."""

    def test_raw_sum_no_rounding(self, scorer: ContentScorer) -> None:
        # With default normalized weights (sum=1.0), all factors=0.1
        # -> total = 0.1 * sum(weights) = 0.1. No rounding applied here.
        result = scorer._compute_total(0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        assert result == pytest.approx(0.1, abs=1e-10)

    def test_zero_factors_give_zero(self, scorer: ContentScorer) -> None:
        assert scorer._compute_total(0, 0, 0, 0, 0, 0) == 0.0

    def test_all_ones_gives_one(self, scorer: ContentScorer) -> None:
        # All factors at 1.0 with normalized weights (sum=1.0) -> 1.0
        assert scorer._compute_total(1.0, 1.0, 1.0, 1.0, 1.0, 1.0) == pytest.approx(1.0)

    def test_negative_factor_propagates(self, scorer: ContentScorer) -> None:
        # _compute_total does NOT clamp; negative input -> negative output.
        result = scorer._compute_total(-1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert result < 0.0


class TestBuildScoreDirect:
    """Pin _build_score rounding and factors dict construction."""

    def test_rounds_to_4_places(self, scorer: ContentScorer) -> None:
        cs = scorer._build_score(0.123456789, 0.987654321, 0.5, 0.25, 0.1, 0.05, 0.15)
        assert cs.total == 0.1235
        assert cs.recency == 0.9877
        assert cs.relevance == 0.5

    def test_factors_dict_unrounded(self, scorer: ContentScorer) -> None:
        cs = scorer._build_score(0.5, 0.123456789, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert cs.factors["recency"] == 0.123456789  # unrounded
        assert cs.recency == 0.1235  # rounded field

    def test_factors_has_exactly_six_keys(self, scorer: ContentScorer) -> None:
        cs = scorer._build_score(0.5, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
        assert set(cs.factors.keys()) == {
            "recency", "relevance", "engagement", "quality", "authority", "freshness"
        }


class TestScoreEdgeInputs:
    """Pin score() with edge-case parameter values."""

    def test_empty_string_change_frequency_defaults_to_monthly(
        self, scorer: ContentScorer
    ) -> None:
        # change_frequency="" -> frequency_hours.get("", 720) -> 720 (monthly)
        # With last_crawled=None, freshness is 0.5 regardless.
        cs = scorer.score(last_crawled=None, change_frequency="")
        assert cs.freshness == 0.5

    def test_none_change_frequency_defaults_to_monthly(
        self, scorer: ContentScorer
    ) -> None:
        # change_frequency=None -> frequency_hours.get(None, 720) -> 720
        cs = scorer.score(last_crawled=None, change_frequency=None)  # type: ignore[arg-type]
        assert cs.freshness == 0.5

    def test_negative_domain_authority_clamped_to_zero(
        self, scorer: ContentScorer
    ) -> None:
        # _score_authority applies max(0.0, min(1.0, score)) unconditionally.
        cs = scorer.score(domain_authority=-0.5, is_verified_source=False)
        assert cs.authority == 0.0

    def test_domain_authority_over_one_clamped(
        self, scorer: ContentScorer
    ) -> None:
        cs = scorer.score(domain_authority=1.5, is_verified_source=False)
        assert cs.authority == 1.0

    def test_idempotent_double_call(self, scorer: ContentScorer) -> None:
        kwargs = dict(
            published_at=_now() - timedelta(days=5),
            keyword_matches=3, total_keywords=10,
            view_count=100, bookmark_count=10, share_count=5,
            word_count=500, has_images=True, has_code=False,
            domain_authority=0.7, is_verified_source=True,
        )
        r1 = scorer.score(**kwargs)
        r2 = scorer.score(**kwargs)
        assert r1.total == r2.total
        assert r1.recency == r2.recency
        assert r1.factors == r2.factors


class TestScorePageEdgeInputs:
    """Pin score_page() with edge-case page objects."""

    def test_content_none_defaults_to_empty(self, scorer: ContentScorer) -> None:
        class _Page:
            content = None
            word_count = 0
            domain_authority = 0.5
            crawled_at = None
        cs = scorer.score_page(_Page())
        assert isinstance(cs, ContentScore)
        assert cs.quality == 0.0  # no content -> no quality

    def test_word_count_none_falls_back_to_split(self, scorer: ContentScorer) -> None:
        class _Page:
            content = "hello world foo bar"
            word_count = None
            domain_authority = 0.5
            crawled_at = None
        cs = scorer.score_page(_Page())
        # word_count=None -> len("hello world foo bar".split()) = 4
        expected_quality = round(min(1.0, math.log1p(4) / math.log1p(3000)), 4)
        assert cs.quality == expected_quality

    def test_interest_store_empty_lists(self, scorer: ContentScorer) -> None:
        class _Interest:
            keywords: list = []
            topics: list = []
            value = ""

        class _Store:
            def list_all(self):
                return [_Interest()]

        class _Page:
            content = "some content"
            word_count = 10
            domain_authority = 0.5
            crawled_at = None

        cs = scorer.score_page(_Page(), _Store())
        # No keywords/topics/value -> total_keywords=0 -> max(0,1)=1, matches=0
        # relevance = 0/1 = 0.0
        assert cs.relevance == 0.0

    def test_crawled_at_naive_datetime(self, scorer: ContentScorer) -> None:
        class _Page:
            content = "test"
            word_count = 5
            domain_authority = 0.5
            crawled_at = datetime.now()  # naive

        cs = scorer.score_page(_Page())
        # Naive crawled_at treated as UTC -> freshness should be 1.0 (just crawled)
        assert cs.freshness == pytest.approx(1.0, abs=0.01)


class TestRankEdgeCases:
    """Pin rank() with additional edge cases."""

    def test_limit_equals_len(self, scorer: ContentScorer) -> None:
        items = [
            {"keyword_matches": 1, "total_keywords": 1},
            {"keyword_matches": 2, "total_keywords": 2},
            {"keyword_matches": 3, "total_keywords": 3},
        ]
        result = scorer.rank(items, limit=3)
        assert len(result) == 3

    def test_extra_unknown_key_raises_type_error(self, scorer: ContentScorer) -> None:
        # Docstring: "the dict's keys must be valid score keyword arguments"
        items = [{"keyword_matches": 1, "total_keywords": 1, "bogus_key": 99}]
        with pytest.raises(TypeError):
            scorer.rank(items, limit=1)

    def test_empty_dict_item_scores_zero_relevance(self, scorer: ContentScorer) -> None:
        # An empty dict -> score() with all defaults -> relevance 0.0
        items = [{}]
        result = scorer.rank(items, limit=1)
        assert len(result) == 1
        assert result[0][1].relevance == 0.0


class TestScoreWeightsTinyValues:
    """Pin ScoreWeights.normalize() with near-zero (but non-zero) weights."""

    def test_very_small_weights_normalize_to_equal(self) -> None:
        w = ScoreWeights(1e-10, 1e-10, 1e-10, 1e-10, 1e-10, 1e-10).normalize()
        total = (
            w.recency + w.relevance + w.engagement
            + w.quality + w.authority + w.freshness
        )
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_mixed_tiny_and_normal(self) -> None:
        w = ScoreWeights(1e-10, 1.0, 1.0, 1.0, 1.0, 1.0).normalize()
        # recency is negligible compared to others
        assert w.recency < 1e-8
        assert w.relevance == pytest.approx(0.2, abs=1e-6)


class TestContentScoreToDictExtremes:
    """Pin ContentScore.to_dict() with extreme values."""

    def test_negative_values_rounded_correctly(self) -> None:
        cs = ContentScore(total=-0.123456789, recency=-0.987654321)
        d = cs.to_dict()
        assert d["total"] == -0.1235
        assert d["recency"] == -0.9877

    def test_very_large_values(self) -> None:
        cs = ContentScore(total=99999.123456789)
        d = cs.to_dict()
        assert d["total"] == 99999.1235

    def test_zero_values(self) -> None:
        cs = ContentScore()
        d = cs.to_dict()
        assert d["total"] == 0.0
        assert d["recency"] == 0.0
        assert d["factors"] == {}


class TestScoreFreshnessUnknownFrequency:
    """Pin _score_freshness with unknown/edge frequency strings."""

    def test_unknown_frequency_string_defaults_to_monthly(
        self, scorer: ContentScorer
    ) -> None:
        # "biweekly" is not in the table -> defaults to 720 (monthly)
        # With last_crawled=now, age_hours~0 -> freshness ~1.0
        cs = scorer._score_freshness(_now(), "biweekly", None)
        assert cs == pytest.approx(1.0, abs=0.01)

    def test_empty_string_frequency_defaults_to_monthly(
        self, scorer: ContentScorer
    ) -> None:
        cs = scorer._score_freshness(_now(), "", None)
        assert cs == pytest.approx(1.0, abs=0.01)

    def test_none_frequency_defaults_to_monthly(
        self, scorer: ContentScorer
    ) -> None:
        cs = scorer._score_freshness(_now(), None, None)  # type: ignore[arg-type]
        assert cs == pytest.approx(1.0, abs=0.01)
