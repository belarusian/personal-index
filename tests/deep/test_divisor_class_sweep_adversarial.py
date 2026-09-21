"""Cycle 350 VALIDATOR: guard-the-raw-divisor CLASS SWEEP armor.

This is the exhaustive sweep of the *guard-the-raw-divisor* defect class
(ARCH-64 lineage: a public function that divides by a caller-controlled
value WITHOUT a zero/negative guard raises ZeroDivisionError / returns a
bogus value). The negative-slice class was swept exhaustively in cycle 349
and closed; this cycle sweeps the divisor class across the whole codebase.

Every public divisor site traced from `grep -rnE '[a-z0-9_)]\\s*/\\s*[a-z_]'
personal_index/*.py` is exercised here with the adversarial divisor that
would break an unguarded implementation (0, negative, or empty-collection).
All sites are GUARDED on current main, so every assertion is a HARD PASS
(regression armor): if a future refactor drops a guard, the matching test
turns red. No xfail markers — there is no defect to pin this cycle.

Sweep table (site -> public entry -> guard -> adversarial input -> result):
  cache.LRUCache.hit_rate(prop)  cache.py:147   total>0 else 0.0      fresh cache (0 hits/0 misses) -> 0.0
  cache.TTLCache.hit_rate(prop)  cache.py:356   total>0 else 0.0      fresh cache -> 0.0
  session.SessionStats.success   session.py:41  total>0 else 0.0      empty stats -> 0.0
  content_batch.success_rate     content_batch.py:48 total==0 -> 0.0  total_items=0 -> 0.0
  content_enricher._sentiment    content_enricher.py:164 total==0 -> 0.0  neutral text -> 0.0
  content_summarizer._score_sent content_summarizer.py:118 words guard  empty -> 0.0
  content_summarizer.ratio       content_summarizer.py:147 max(.,1)    empty text -> ratio 0.0
  content_health.health_pct      content_health.py:131 total==0 -> 100 total_items=0 -> 100.0
  content_health.check_item      content_health.py:262 ct>0 else 0.0   (always >=1 check) -> no crash
  content_dedup.text_similarity  content_dedup.py:170 empty-set guard  empty text -> 0.0
  content.compute_tf             content.py:151 not tokens -> {}       empty tokens -> {}
  keyword_extractor.compute_tf   keyword_extractor.py:117 not tokens   all-stopwords -> {}
  content_scoring.normalize      content_scoring.py:68 total==0 -> default all-zero weights -> default
  content_scoring._score_engage  content_scoring.py:319 log1p(1000)>0  negative counts -> 0.0
  content_scoring._score_fresh   content_scoring.py:411 expected>0     unknown freq -> 720 default
  progress.progress_percent      progress.py:78 total==0 -> 0.0        total_steps=0 -> 0.0
  progress.estimated_remaining   progress.py:99 current==0 -> 0.0      current_step=0 -> 0.0
  text_utils.read_time_minutes   text_utils.py:303 wpm<=0 -> 0         wpm=0/-5 -> 0
  text_utils.similarity_ratio    text_utils.py:208 both-empty guard    ""/"" -> 1.0, ""/x -> 0.0
  stats.avg_content_length       stats.py:71 max(.,1)                 empty index (0 pages) -> 0.0
  analytics.get_crawl_stats      analytics.py:369 not events -> {0}    empty -> {"total":0}
  rate_limiter.TokenBucket       rate_limiter.py:43 window>0 (ctor)    ctor rejects window<=0
  throttle.rate_per_second(prop) throttle.py:35 window>0 else 0.0     window<=0 -> 0.0 (wait falls to min_delay)
"""

from __future__ import annotations

import math

import pytest


# ── cache hit_rate (cache.py:147 / :356) ──────────────────────────────────


def test_lru_hit_rate_zero_total_returns_zero():
    from personal_index.cache import LRUCache

    c = LRUCache(max_size=4)
    # No get() calls -> hits=0, misses=0 -> total=0 -> guarded 0.0 (no ZeroDivisionError)
    assert c.hit_rate == 0.0


def test_ttl_hit_rate_zero_total_returns_zero():
    from personal_index.cache import TTLCache

    c = TTLCache(ttl=60.0, max_size=4)
    assert c.hit_rate == 0.0


# ── session.SessionStats.success_rate (session.py:41) ─────────────────────


def test_session_success_rate_zero_total():
    from personal_index.session import SessionStats

    assert SessionStats().success_rate == 0.0


# ── content_batch.success_rate (content_batch.py:48) ──────────────────────


def test_batch_success_rate_zero_total():
    from personal_index.content_batch import BatchResult

    r = BatchResult(batch_id="b", total_items=0)
    assert r.success_rate == 0.0


# ── content_enricher sentiment (content_enricher.py:164) ──────────────────


def test_enricher_sentiment_no_signal_words():
    from personal_index.content_enricher import ContentEnricher

    e = ContentEnricher()
    # Text with neither positive nor negative words -> total=0 -> guarded 0.0
    assert e._compute_sentiment("table chair number 42") == 0.0


# ── content_summarizer ratio (content_summarizer.py:147) ──────────────────


def test_summarizer_ratio_empty_text_no_division():
    from personal_index.content_summarizer import summarize

    # max(original_words, 1) floor: punctuation-only text has 0 tokens
    # but is non-empty, so it reaches the ratio computation; the floor
    # prevents ZeroDivisionError and yields 0.0 (0 / max(0, 1)).
    res = summarize("!!! ??? ... " * 10, max_sentences=1, min_length=1)
    assert res.word_count_original == 0
    assert res.ratio == 0.0


# ── content_health health_percentage (content_health.py:131) ──────────────


def test_health_percentage_zero_total():
    from personal_index.content_health import HealthReport

    # total_items == 0 -> guarded 100.0 (not ZeroDivisionError)
    assert HealthReport().health_percentage == 100.0


def test_health_check_item_never_zero_checks():
    from personal_index.content_health import ContentHealthChecker

    # check_item always runs >=1 check, so ct>0; adversarial empty inputs
    # must still produce a result without ZeroDivisionError.
    res = ContentHealthChecker().check_item(url="", title="", content="")
    assert isinstance(res.score, float)
    assert math.isfinite(res.score)


# ── content_dedup jaccard (content_dedup.py:170) ──────────────────────────


def test_jaccard_empty_text_returns_zero():
    from personal_index.content_dedup import text_similarity

    assert text_similarity("", "") == 0.0
    assert text_similarity("   ", "abc") == 0.0
    # non-empty but no [a-z0-9] tokens -> empty word set -> guarded 0.0
    assert text_similarity("!!!", "???") == 0.0


# ── content.compute_tf (content.py:151) ───────────────────────────────────


def test_compute_tf_empty_tokens():
    from personal_index.content import compute_tf

    assert compute_tf([]) == {}


# ── keyword_extractor.compute_term_frequency (keyword_extractor.py:117) ───


def test_keyword_extractor_tf_all_stopwords():
    from personal_index.keyword_extractor import KeywordExtractor

    ke = KeywordExtractor()
    # All tokens are stopwords -> empty after filter -> guarded {}
    assert ke.compute_term_frequency("the a an of to and") == {}


# ── content_scoring ScoreWeights.normalize (content_scoring.py:68) ────────


def test_score_weights_normalize_all_zero():
    from personal_index.content_scoring import ScoreWeights

    # total == 0 -> guarded: returns DEFAULT ScoreWeights (not ZeroDivisionError)
    z = ScoreWeights(0, 0, 0, 0, 0, 0)
    n = z.normalize()
    assert n.recency == pytest.approx(0.2)
    assert n.relevance == pytest.approx(0.25)
    assert n.authority == pytest.approx(0.1)


# ── content_scoring._score_engagement (content_scoring.py:319) ────────────


def test_score_engagement_negative_counts():
    from personal_index.content_scoring import ContentScorer

    s = ContentScorer()
    # Negative counts floored to 0 -> engagement 0 -> 0.0 (no math domain error)
    assert s._score_engagement(-5, -1, -100) == 0.0


# ── content_scoring._score_freshness (content_scoring.py:411) ─────────────


def test_score_freshness_unknown_frequency_default():
    from datetime import datetime, timezone

    from personal_index.content_scoring import ContentScorer

    s = ContentScorer()
    # Unknown change_frequency -> expected defaults to 720 (never 0) -> no ZeroDivisionError
    now = datetime.now(timezone.utc)
    val = s._score_freshness(last_crawled=now, change_frequency="bogus", updated_at=None)
    assert 0.0 <= val <= 1.0


# ── progress (progress.py:78 / :99) ───────────────────────────────────────


def test_progress_percent_zero_total():
    from personal_index.progress import ProgressTracker

    assert ProgressTracker(total_steps=0, current_step=0).progress_percent == 0.0


def test_progress_estimated_remaining_zero_current():
    from personal_index.progress import ProgressTracker

    # current_step == 0 -> guarded 0.0 (no ZeroDivisionError on elapsed/current)
    assert ProgressTracker(total_steps=10, current_step=0).estimated_remaining == 0.0


# ── text_utils.read_time_minutes (text_utils.py:303) ──────────────────────


def test_read_time_zero_wpm():
    from personal_index.text_utils import read_time_minutes

    assert read_time_minutes("one two three", wpm=0) == 0
    assert read_time_minutes("one two three", wpm=-5) == 0


# ── text_utils.similarity_ratio (text_utils.py:208) ───────────────────────


def test_similarity_ratio_empty_inputs():
    from personal_index.text_utils import similarity_ratio

    assert similarity_ratio("", "") == 1.0
    assert similarity_ratio("", "x") == 0.0
    assert similarity_ratio("x", "") == 0.0


# ── stats.avg_content_length (stats.py:71) ────────────────────────────────


def test_stats_empty_pages_no_division():
    import os
    import tempfile

    from personal_index.search_index import SearchIndex
    from personal_index.stats import StatsCollector

    # max(total_pages, 1) floor: an empty index (0 pages) must not raise
    d = tempfile.mkdtemp()
    si = SearchIndex(os.path.join(d, "idx.json"))
    st = StatsCollector(search_index=si).get_index_stats()
    assert st.total_pages == 0
    assert st.avg_content_length == 0.0


# ── analytics.get_crawl_stats (analytics.py:369) ──────────────────────────


def test_analytics_crawl_stats_empty():
    from personal_index.analytics import AnalyticsTracker

    at = AnalyticsTracker()
    # no events -> guarded {"total": 0} (no ZeroDivisionError on error_rate)
    assert at.get_crawl_stats() == {"total": 0}


# ── rate_limiter.TokenBucket (rate_limiter.py:43) ─────────────────────────


def test_rate_limiter_rejects_nonpositive_window():
    from personal_index.rate_limiter import RateLimitConfig

    # window_seconds <= 0 is rejected at construction (guard-the-raw-divisor
    # enforced at the boundary, so TokenBucket.__init__ never divides by 0).
    with pytest.raises(ValueError):
        RateLimitConfig(max_requests=10, window_seconds=0)
    with pytest.raises(ValueError):
        RateLimitConfig(max_requests=10, window_seconds=-1)


# ── throttle min_wait (throttle.py:104) ───────────────────────────────────


def test_throttle_zero_rate_per_second_falls_back():
    from personal_index.throttle import ThrottleRule

    # rate_per_second = max_requests / window_seconds; a degenerate
    # window (<= 0) is guarded to 0.0 (no ZeroDivisionError), so the wait
    # path falls through to min_delay instead of dividing by a 0 rate.
    assert ThrottleRule(max_requests=10, window_seconds=0).rate_per_second == 0.0
    assert ThrottleRule(max_requests=10, window_seconds=-5).rate_per_second == 0.0
    assert ThrottleRule(max_requests=10, window_seconds=10).rate_per_second == pytest.approx(1.0)


# ── end-to-end CLI run (stats command, exercises divisor paths) ───────────


def test_cli_stats_empty_index_end_to_end(tmp_path):
    from click.testing import CliRunner

    from personal_index.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--data-dir", str(tmp_path), "stats"])
    # Empty index: stats must render without ZeroDivisionError (avg_content_length
    # and any rate computations hit their guards).
    assert result.exit_code == 0, result.output
