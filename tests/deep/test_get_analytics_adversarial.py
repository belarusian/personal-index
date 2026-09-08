"""Adversarial deep tests for AnalyticsTracker.get_analytics.

Contract source: personal_index/analytics.py docstring for get_analytics
(the merge of _compute_search_analytics + _compute_crawl_analytics into one
AnalyticsData). These tests pin the documented merge behavior against
adversarial inputs: both-empty guard path, search-only / crawl-only
asymmetry, the guarantee that total_pages_indexed is never set, top_n
out-of-range, unicode, purity (no mutation of the event lists), idempotence,
fresh-instance-per-call, and one end-to-end CLI run.
"""

from __future__ import annotations

import copy

import pytest

from personal_index.analytics import (
    AnalyticsData,
    AnalyticsTracker,
    CrawlEvent,
    SearchEvent,
)


def _tracker() -> AnalyticsTracker:
    return AnalyticsTracker()


def _search(query: str, duration_ms: float = 0.0, timestamp: str = "") -> SearchEvent:
    return SearchEvent(query=query, duration_ms=duration_ms, timestamp=timestamp)


def _crawl(url: str, status_code: int = 200, duration_ms: float = 0.0,
           error: str | None = None) -> CrawlEvent:
    return CrawlEvent(url=url, status_code=status_code, duration_ms=duration_ms,
                      error=error)


# --- Guard path: both event lists empty -----------------------------------

def test_both_empty_all_defaults():
    """Both lists empty -> merged result is all zeros/empty."""
    t = _tracker()
    data = t.get_analytics(top_n=10)
    assert data.total_searches == 0
    assert data.total_crawls == 0
    assert data.total_pages_indexed == 0
    assert data.avg_search_duration_ms == 0.0
    assert data.avg_crawl_duration_ms == 0.0
    assert data.top_queries == []
    assert data.top_domains == []
    assert data.hourly_searches == {}
    assert data.daily_searches == {}
    assert data.success_count == 0
    assert data.error_count == 0


def test_both_empty_returns_analytics_data():
    t = _tracker()
    assert isinstance(t.get_analytics(), AnalyticsData)


# --- Search-only asymmetry ------------------------------------------------

def test_search_only_crawl_fields_default():
    """Only search events -> search fields populated, crawl fields default."""
    t = _tracker()
    t.record_search("alpha", duration_ms=100.0)
    t.record_search("alpha", duration_ms=200.0)
    t.record_search("beta", duration_ms=0.0)
    data = t.get_analytics(top_n=10)
    # search fields
    assert data.total_searches == 3
    assert data.avg_search_duration_ms == pytest.approx(150.0)
    assert data.top_queries[0] == ("alpha", 2)
    # crawl fields stay at defaults
    assert data.total_crawls == 0
    assert data.avg_crawl_duration_ms == 0.0
    assert data.top_domains == []
    assert data.success_count == 0
    assert data.error_count == 0


# --- Crawl-only asymmetry -------------------------------------------------

def test_crawl_only_search_fields_default():
    """Only crawl events -> crawl fields populated, search fields default."""
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, duration_ms=100.0)
    t.record_crawl("https://a.com/2", status_code=404, duration_ms=200.0)
    data = t.get_analytics(top_n=10)
    # crawl fields
    assert data.total_crawls == 2
    assert data.avg_crawl_duration_ms == pytest.approx(150.0)
    assert data.top_domains[0] == ("a.com", 2)
    assert data.success_count == 1
    assert data.error_count == 1
    # search fields stay at defaults
    assert data.total_searches == 0
    assert data.avg_search_duration_ms == 0.0
    assert data.top_queries == []
    assert data.hourly_searches == {}
    assert data.daily_searches == {}


# --- Both populated: correct merge ----------------------------------------

def test_both_populated_merge():
    t = _tracker()
    t.record_search("q1", duration_ms=10.0)
    t.record_search("q1", duration_ms=30.0)
    t.record_search("q2", duration_ms=0.0)
    t.record_crawl("https://x.com/a", status_code=200, duration_ms=100.0)
    t.record_crawl("https://x.com/b", status_code=200, duration_ms=200.0)
    t.record_crawl("https://y.com/c", status_code=500, duration_ms=0.0)
    data = t.get_analytics(top_n=10)
    # search side
    assert data.total_searches == 3
    assert data.avg_search_duration_ms == pytest.approx(20.0)
    assert data.top_queries[0] == ("q1", 2)
    # crawl side
    assert data.total_crawls == 3
    assert data.avg_crawl_duration_ms == pytest.approx(150.0)
    assert data.top_domains[0] == ("x.com", 2)
    assert data.success_count == 2
    assert data.error_count == 1
    # never-set field
    assert data.total_pages_indexed == 0


# --- total_pages_indexed is never set -------------------------------------

def test_total_pages_indexed_never_set():
    """total_pages_indexed stays 0 regardless of event volume."""
    t = _tracker()
    for i in range(20):
        t.record_search(f"q{i}", duration_ms=5.0)
        t.record_crawl(f"https://d{i}.com/p", status_code=200, duration_ms=5.0)
    data = t.get_analytics(top_n=10)
    assert data.total_pages_indexed == 0


# --- top_n out-of-range ---------------------------------------------------

def test_top_n_zero_truncates_both():
    t = _tracker()
    t.record_search("a")
    t.record_search("b")
    t.record_crawl("https://a.com/1")
    t.record_crawl("https://b.com/1")
    data = t.get_analytics(top_n=0)
    assert data.top_queries == []
    assert data.top_domains == []
    # counts still correct
    assert data.total_searches == 2
    assert data.total_crawls == 2


def test_top_n_negative_returns_empty():
    """most_common(negative) returns [] (Counter semantics), not all entries."""
    t = _tracker()
    t.record_search("a")
    t.record_search("a")
    t.record_search("b")
    t.record_crawl("https://a.com/1")
    t.record_crawl("https://b.com/1")
    data = t.get_analytics(top_n=-1)
    assert data.top_queries == []
    assert data.top_domains == []
    # counts still correct
    assert data.total_searches == 3
    assert data.total_crawls == 2


def test_top_n_greater_than_len():
    t = _tracker()
    t.record_search("a")
    t.record_crawl("https://a.com/1")
    data = t.get_analytics(top_n=1000)
    assert len(data.top_queries) == 1
    assert len(data.top_domains) == 1


# --- Unicode --------------------------------------------------------------

def test_unicode_query_and_domain():
    t = _tracker()
    t.record_search("café search")
    t.record_search("café search")
    t.record_crawl("https://münchen.example/x")
    data = t.get_analytics(top_n=10)
    assert data.top_queries[0] == ("café search", 2)
    assert data.top_domains[0] == ("münchen.example", 1)


# --- Purity: no mutation of event lists -----------------------------------

def test_purity_no_mutation_of_search_events():
    t = _tracker()
    t.record_search("a", duration_ms=10.0)
    t.record_search("b", duration_ms=20.0)
    before = copy.deepcopy(t._search_events)
    t.get_analytics(top_n=10)
    assert t._search_events == before


def test_purity_no_mutation_of_crawl_events():
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, duration_ms=10.0)
    t.record_crawl("https://b.com/2", status_code=404, duration_ms=20.0)
    before = copy.deepcopy(t._crawl_events)
    t.get_analytics(top_n=10)
    assert t._crawl_events == before


# --- Idempotence ----------------------------------------------------------

def test_idempotence_repeated_calls():
    t = _tracker()
    t.record_search("a", duration_ms=10.0)
    t.record_crawl("https://a.com/1", status_code=200, duration_ms=10.0)
    first = t.get_analytics(top_n=10)
    second = t.get_analytics(top_n=10)
    assert first == second


def test_idempotence_event_counts_stable():
    """Calling get_analytics does not grow the event lists."""
    t = _tracker()
    t.record_search("a")
    t.record_crawl("https://a.com/1")
    for _ in range(5):
        t.get_analytics(top_n=10)
    assert len(t._search_events) == 1
    assert len(t._crawl_events) == 1


# --- Fresh instance per call ----------------------------------------------

def test_fresh_instance_per_call():
    """Two trackers with identical events produce independent results."""
    t1 = _tracker()
    t2 = _tracker()
    t1.record_search("a", duration_ms=10.0)
    t2.record_search("a", duration_ms=10.0)
    d1 = t1.get_analytics(top_n=10)
    d2 = t2.get_analytics(top_n=10)
    assert d1 == d2
    # mutating one result must not affect the other
    d1.top_queries.append(("zzz", 99))
    assert ("zzz", 99) not in d2.top_queries


# --- Round-trip: record then compute --------------------------------------

def test_round_trip_record_then_compute():
    t = _tracker()
    t.record_search(SearchEvent(query="python", duration_ms=120.0,
                                timestamp="2026-01-02T03:04:05+00:00"))
    t.record_search(SearchEvent(query="python", duration_ms=80.0,
                                timestamp="2026-01-02T03:30:00+00:00"))
    t.record_search(SearchEvent(query="rust", duration_ms=0.0,
                                timestamp="2026-01-03T09:00:00+00:00"))
    t.record_crawl("https://docs.python.org/3", status_code=200, duration_ms=50.0)
    t.record_crawl("https://example.com/404", status_code=404, duration_ms=0.0)
    data = t.get_analytics(top_n=10)
    assert data.total_searches == 3
    assert data.avg_search_duration_ms == pytest.approx(100.0)
    assert data.top_queries[0] == ("python", 2)
    # hourly buckets: 03:00 (two events), 09:00 (one event)
    assert data.hourly_searches == {"03:00": 2, "09:00": 1}
    # daily buckets
    assert data.daily_searches == {"2026-01-02": 2, "2026-01-03": 1}
    assert data.total_crawls == 2
    assert data.success_count == 1
    assert data.error_count == 1


def test_round_trip_invalid_timestamps_skipped():
    """Timestamps failing fromisoformat are skipped in hourly/daily."""
    t = _tracker()
    t.record_search(SearchEvent(query="a", timestamp="not-a-timestamp"))
    t.record_search(SearchEvent(query="b", timestamp="2026-05-06T07:08:09+00:00"))
    data = t.get_analytics(top_n=10)
    assert data.total_searches == 2
    assert data.hourly_searches == {"07:00": 1}
    assert data.daily_searches == {"2026-05-06": 1}


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
