"""Adversarial deep tests for AnalyticsTracker._compute_search_analytics.

Contract source: personal_index/analytics.py docstring (exact contract merged
via #980). These tests pin the documented behavior against adversarial inputs:
empty event list, zero/negative durations, unparseable timestamps, top_n
out-of-range, unicode queries, and the guarantee that crawl fields are never
touched by the search computation.
"""

from __future__ import annotations


import pytest

from personal_index.analytics import AnalyticsData, AnalyticsTracker, SearchEvent


def _tracker() -> AnalyticsTracker:
    return AnalyticsTracker()


def _event(query: str, duration_ms: float = 0.0, timestamp: str = "") -> SearchEvent:
    return SearchEvent(query=query, duration_ms=duration_ms, timestamp=timestamp)


# --- Guard path: empty event list -----------------------------------------

def test_empty_events_guard_path():
    """Empty _search_events -> all search fields stay at defaults."""
    t = _tracker()
    data = t._compute_search_analytics(top_n=10)
    assert data.total_searches == 0
    assert data.avg_search_duration_ms == 0.0
    assert data.top_queries == []
    assert data.hourly_searches == {}
    assert data.daily_searches == {}


def test_empty_events_crawl_fields_untouched():
    """Search computation must not touch crawl fields (stay at defaults)."""
    t = _tracker()
    data = t._compute_search_analytics(top_n=10)
    assert data.total_crawls == 0
    assert data.top_domains == []
    assert data.avg_crawl_duration_ms == 0.0
    assert data.success_count == 0
    assert data.error_count == 0


# --- total_searches always equals len(events) -----------------------------

def test_total_searches_equals_event_count():
    t = _tracker()
    for i in range(5):
        t.record_search(f"q{i}")
    data = t._compute_search_analytics(top_n=10)
    assert data.total_searches == 5


# --- avg_search_duration_ms: only > 0 durations count ---------------------

def test_avg_duration_excludes_zero_and_negative():
    t = _tracker()
    t.record_search("a", duration_ms=100.0)
    t.record_search("b", duration_ms=0.0)      # excluded
    t.record_search("c", duration_ms=-50.0)    # excluded
    t.record_search("d", duration_ms=300.0)
    data = t._compute_search_analytics(top_n=10)
    # mean of [100, 300] = 200
    assert data.avg_search_duration_ms == pytest.approx(200.0)


def test_avg_duration_all_zero_stays_zero():
    t = _tracker()
    t.record_search("a", duration_ms=0.0)
    t.record_search("b", duration_ms=0.0)
    data = t._compute_search_analytics(top_n=10)
    assert data.avg_search_duration_ms == 0.0


def test_avg_duration_all_negative_stays_zero():
    t = _tracker()
    t.record_search("a", duration_ms=-1.0)
    data = t._compute_search_analytics(top_n=10)
    assert data.avg_search_duration_ms == 0.0


# --- top_queries: Counter.most_common(top_n) ------------------------------

def test_top_queries_most_common_ordering():
    t = _tracker()
    t.record_search("common")
    t.record_search("common")
    t.record_search("common")
    t.record_search("rare")
    data = t._compute_search_analytics(top_n=10)
    assert data.top_queries[0] == ("common", 3)
    assert ("rare", 1) in data.top_queries


def test_top_queries_truncates_to_top_n():
    t = _tracker()
    for i in range(10):
        t.record_search(f"q{i}")
    data = t._compute_search_analytics(top_n=3)
    assert len(data.top_queries) == 3


def test_top_queries_top_n_zero_returns_empty():
    t = _tracker()
    t.record_search("a")
    t.record_search("b")
    data = t._compute_search_analytics(top_n=0)
    assert data.top_queries == []


def test_top_queries_top_n_larger_than_distinct():
    t = _tracker()
    t.record_search("a")
    t.record_search("b")
    data = t._compute_search_analytics(top_n=100)
    assert len(data.top_queries) == 2


def test_top_queries_unicode():
    t = _tracker()
    t.record_search("café")
    t.record_search("café")
    t.record_search("日本語")
    data = t._compute_search_analytics(top_n=10)
    assert ("café", 2) in data.top_queries
    assert ("日本語", 1) in data.top_queries


# --- hourly/daily buckets: unparseable timestamps skipped -----------------

def test_hourly_daily_bucketing():
    t = _tracker()
    t.record_search(_event("a", timestamp="2026-01-02T03:04:05+00:00"))
    t.record_search(_event("b", timestamp="2026-01-02T03:59:59+00:00"))
    t.record_search(_event("c", timestamp="2026-01-02T04:00:00+00:00"))
    data = t._compute_search_analytics(top_n=10)
    assert data.hourly_searches == {"03:00": 2, "04:00": 1}
    assert data.daily_searches == {"2026-01-02": 3}


def test_unparseable_timestamps_skipped_silently():
    t = _tracker()
    t.record_search(_event("a", timestamp="not-a-timestamp"))
    t.record_search(_event("b", timestamp="2026-01-02T03:04:05+00:00"))
    data = t._compute_search_analytics(top_n=10)
    # only the parseable one is bucketed
    assert data.hourly_searches == {"03:00": 1}
    assert data.daily_searches == {"2026-01-02": 1}
    # but total_searches still counts both
    assert data.total_searches == 2


def test_empty_timestamp_string_skipped():
    """SearchEvent auto-fills empty timestamps, so this is parseable; but a
    manually-constructed event with a garbage timestamp is skipped."""
    t = _tracker()
    ev = SearchEvent(query="x", timestamp="")
    # __post_init__ fills it, so it becomes parseable
    t._search_events.append(ev)
    data = t._compute_search_analytics(top_n=10)
    assert data.total_searches == 1
    assert len(data.daily_searches) == 1


# --- idempotence: repeated calls give same result -------------------------

def test_idempotence_repeated_calls():
    t = _tracker()
    t.record_search(_event("a", duration_ms=10.0, timestamp="2026-01-02T03:04:05+00:00"))
    t.record_search(_event("b", duration_ms=20.0, timestamp="2026-01-02T03:05:05+00:00"))
    d1 = t._compute_search_analytics(top_n=10)
    d2 = t._compute_search_analytics(top_n=10)
    assert d1.total_searches == d2.total_searches
    assert d1.avg_search_duration_ms == d2.avg_search_duration_ms
    assert d1.top_queries == d2.top_queries
    assert d1.hourly_searches == d2.hourly_searches
    assert d1.daily_searches == d2.daily_searches


# --- returns a fresh AnalyticsData each call ------------------------------

def test_returns_fresh_instance_each_call():
    t = _tracker()
    t.record_search("a")
    d1 = t._compute_search_analytics(top_n=10)
    d2 = t._compute_search_analytics(top_n=10)
    assert d1 is not d2
    assert isinstance(d1, AnalyticsData)
    assert isinstance(d2, AnalyticsData)


# --- end-to-end: record via public API then compute -----------------------

def test_end_to_end_record_then_compute():
    t = _tracker()
    t.record_search("python", result_count=3, duration_ms=150.0)
    t.record_search("python", result_count=1, duration_ms=250.0)
    t.record_search("rust", result_count=2, duration_ms=0.0)
    data = t._compute_search_analytics(top_n=10)
    assert data.total_searches == 3
    # mean of [150, 250] = 200 (the 0.0 is excluded)
    assert data.avg_search_duration_ms == pytest.approx(200.0)
    assert data.top_queries[0] == ("python", 2)


# --- end-to-end CLI run ---------------------------------------------------

def test_end_to_end_cli_init_and_stats(tmp_path):
    """End-to-end: init a data dir and run stats through the installed CLI."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["stats", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    import json as _json
    payload = _json.loads(r.output)
    assert payload["indexed_pages"] == 0
    assert payload["interests"] == 0
    assert payload["total_tags"] == 0
