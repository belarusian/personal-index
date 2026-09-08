"""Adversarial deep tests for AnalyticsTracker.get_search_stats / get_crawl_stats.

Contract source: personal_index/analytics.py docstrings for get_search_stats
and get_crawl_stats. These tests pin the documented per-event statistics
behavior against adversarial inputs: the exact guard path ({"total": 0} with
NO other keys), the duration/content-size > 0 filtering, the truthy
clicked_url / error counting, the distinct-query count, the unfiltered
status_codes Counter, purity (no mutation of the event lists), idempotence,
round-trips through record_search / record_crawl, and one end-to-end CLI run.
"""

from __future__ import annotations

import copy

import pytest

from personal_index.analytics import AnalyticsTracker, CrawlEvent, SearchEvent


def _tracker() -> AnalyticsTracker:
    return AnalyticsTracker()


def _search(query: str, result_count: int = 0, clicked_url: str | None = None,
            duration_ms: float = 0.0) -> SearchEvent:
    return SearchEvent(query=query, result_count=result_count,
                       clicked_url=clicked_url, duration_ms=duration_ms)


def _crawl(url: str, status_code: int = 200, content_size: int = 0,
           duration_ms: float = 0.0, error: str | None = None) -> CrawlEvent:
    return CrawlEvent(url=url, status_code=status_code, content_size=content_size,
                      duration_ms=duration_ms, error=error)


# --- get_search_stats: guard path -----------------------------------------

def test_search_stats_guard_exact_keys():
    """No search events -> exactly {"total": 0}, no other keys."""
    t = _tracker()
    out = t.get_search_stats()
    assert out == {"total": 0}
    assert set(out.keys()) == {"total"}


def test_search_stats_guard_when_only_crawl_events():
    """Crawl events present but no search events -> still {"total": 0}."""
    t = _tracker()
    t.record_crawl("https://a.example")
    out = t.get_search_stats()
    assert out == {"total": 0}
    assert set(out.keys()) == {"total"}


# --- get_search_stats: normal path ----------------------------------------

def test_search_stats_total_equals_event_count():
    t = _tracker()
    for q in ("a", "b", "c", "d"):
        t.record_search(q)
    assert t.get_search_stats()["total"] == 4


def test_search_stats_avg_results_mean():
    t = _tracker()
    for rc in (1, 2, 3, 4):
        t.record_search("q", result_count=rc)
    assert t.get_search_stats()["avg_results"] == pytest.approx(2.5)


def test_search_stats_max_min_results():
    t = _tracker()
    for rc in (5, 1, 9, 3):
        t.record_search("q", result_count=rc)
    out = t.get_search_stats()
    assert out["max_results"] == 9
    assert out["min_results"] == 1


def test_search_stats_negative_result_count_pinned():
    """result_count is an int with no documented floor; pin the arithmetic."""
    t = _tracker()
    t.record_search("q", result_count=-4)
    t.record_search("q", result_count=2)
    out = t.get_search_stats()
    assert out["min_results"] == -4
    assert out["max_results"] == 2
    assert out["avg_results"] == pytest.approx(-1.0)


def test_search_stats_duration_only_over_positive():
    """avg/max duration computed only over duration_ms > 0."""
    t = _tracker()
    t.record_search("q", duration_ms=0.0)
    t.record_search("q", duration_ms=-5.0)
    t.record_search("q", duration_ms=10.0)
    t.record_search("q", duration_ms=20.0)
    out = t.get_search_stats()
    assert out["avg_duration_ms"] == pytest.approx(15.0)
    assert out["max_duration_ms"] == pytest.approx(20.0)


def test_search_stats_duration_all_nonpositive_zero():
    """No duration_ms > 0 -> avg/max duration both 0."""
    t = _tracker()
    t.record_search("q", duration_ms=0.0)
    t.record_search("q", duration_ms=-3.0)
    out = t.get_search_stats()
    assert out["avg_duration_ms"] == 0
    assert out["max_duration_ms"] == 0


def test_search_stats_click_through_rate_truthy():
    """clicked_url counted only when truthy; empty string is falsy."""
    t = _tracker()
    t.record_search("q", clicked_url="https://x.example")
    t.record_search("q", clicked_url="")          # falsy
    t.record_search("q", clicked_url=None)        # falsy
    t.record_search("q", clicked_url="https://y.example")
    assert t.get_search_stats()["click_through_rate"] == pytest.approx(0.5)


def test_search_stats_unique_queries_distinct():
    t = _tracker()
    for q in ("a", "a", "b", "b", "b", "c"):
        t.record_search(q)
    assert t.get_search_stats()["unique_queries"] == 3


def test_search_stats_unique_queries_whitespace_and_unicode_distinct():
    """Whitespace and unicode queries are distinct strings, not normalized."""
    t = _tracker()
    t.record_search("  ")
    t.record_search("")
    t.record_search("café")
    t.record_search("cafe")
    t.record_search("café")
    out = t.get_search_stats()
    # "  ", "", "café", "cafe" are 4 distinct strings
    assert out["unique_queries"] == 4
    assert out["total"] == 5


# --- get_search_stats: purity + idempotence --------------------------------

def test_search_stats_purity_no_mutation():
    t = _tracker()
    t.record_search("a", result_count=3, duration_ms=7.0)
    t.record_search("b", result_count=1)
    before = copy.deepcopy(t._search_events)
    t.get_search_stats()
    t.get_search_stats()
    assert t._search_events == before


def test_search_stats_idempotent():
    t = _tracker()
    t.record_search("a", result_count=2, duration_ms=5.0,
                    clicked_url="https://x.example")
    t.record_search("a", result_count=4)
    first = t.get_search_stats()
    second = t.get_search_stats()
    assert first == second


# --- get_crawl_stats: guard path ------------------------------------------

def test_crawl_stats_guard_exact_keys():
    t = _tracker()
    out = t.get_crawl_stats()
    assert out == {"total": 0}
    assert set(out.keys()) == {"total"}


def test_crawl_stats_guard_when_only_search_events():
    t = _tracker()
    t.record_search("q")
    out = t.get_crawl_stats()
    assert out == {"total": 0}
    assert set(out.keys()) == {"total"}


# --- get_crawl_stats: normal path -----------------------------------------

def test_crawl_stats_total_equals_event_count():
    t = _tracker()
    for u in ("https://a", "https://b", "https://c"):
        t.record_crawl(u)
    assert t.get_crawl_stats()["total"] == 3


def test_crawl_stats_duration_only_over_positive():
    t = _tracker()
    t.record_crawl("https://a", duration_ms=0.0)
    t.record_crawl("https://a", duration_ms=-2.0)
    t.record_crawl("https://a", duration_ms=10.0)
    t.record_crawl("https://a", duration_ms=30.0)
    out = t.get_crawl_stats()
    assert out["avg_duration_ms"] == pytest.approx(20.0)


def test_crawl_stats_duration_all_nonpositive_zero():
    t = _tracker()
    t.record_crawl("https://a", duration_ms=0.0)
    t.record_crawl("https://a", duration_ms=-1.0)
    assert t.get_crawl_stats()["avg_duration_ms"] == 0


def test_crawl_stats_content_size_only_over_positive():
    """avg/total content_size computed only over content_size > 0."""
    t = _tracker()
    t.record_crawl("https://a", content_size=0)
    t.record_crawl("https://a", content_size=-100)
    t.record_crawl("https://a", content_size=100)
    t.record_crawl("https://a", content_size=300)
    out = t.get_crawl_stats()
    assert out["avg_content_size"] == pytest.approx(200.0)
    assert out["total_content_size"] == 400


def test_crawl_stats_content_size_all_nonpositive_zero():
    t = _tracker()
    t.record_crawl("https://a", content_size=0)
    t.record_crawl("https://a", content_size=-5)
    out = t.get_crawl_stats()
    assert out["avg_content_size"] == 0
    assert out["total_content_size"] == 0


def test_crawl_stats_status_codes_unfiltered_counter():
    """status_codes counts ALL events, including zero and out-of-range codes."""
    t = _tracker()
    t.record_crawl("https://a", status_code=200)
    t.record_crawl("https://a", status_code=200)
    t.record_crawl("https://a", status_code=404)
    t.record_crawl("https://a", status_code=0)
    t.record_crawl("https://a", status_code=999)
    out = t.get_crawl_stats()
    assert out["status_codes"] == {200: 2, 404: 1, 0: 1, 999: 1}
    assert sum(out["status_codes"].values()) == out["total"] == 5


def test_crawl_stats_error_rate_truthy():
    """error counted only when truthy; empty string is falsy."""
    t = _tracker()
    t.record_crawl("https://a", error="timeout")
    t.record_crawl("https://a", error="")
    t.record_crawl("https://a", error=None)
    t.record_crawl("https://a", error="dns")
    assert t.get_crawl_stats()["error_rate"] == pytest.approx(0.5)


def test_crawl_stats_unicode_url_and_error():
    t = _tracker()
    t.record_crawl("https://café.example/путь", status_code=200,
                   content_size=10, error="ошибка")
    out = t.get_crawl_stats()
    assert out["total"] == 1
    assert out["status_codes"] == {200: 1}
    assert out["error_rate"] == pytest.approx(1.0)


# --- get_crawl_stats: purity + idempotence ---------------------------------

def test_crawl_stats_purity_no_mutation():
    t = _tracker()
    t.record_crawl("https://a", status_code=500, content_size=10,
                   duration_ms=5.0, error="boom")
    before = copy.deepcopy(t._crawl_events)
    t.get_crawl_stats()
    t.get_crawl_stats()
    assert t._crawl_events == before


def test_crawl_stats_idempotent():
    t = _tracker()
    t.record_crawl("https://a", status_code=200, content_size=100,
                   duration_ms=5.0)
    t.record_crawl("https://b", status_code=404, error="nf")
    assert t.get_crawl_stats() == t.get_crawl_stats()


# --- round-trips through record_* -----------------------------------------

def test_search_stats_round_trip_via_record_search():
    t = _tracker()
    t.record_search("python", result_count=7, duration_ms=12.0,
                    clicked_url="https://py.example")
    t.record_search("python", result_count=3)
    t.record_search("rust", result_count=5, duration_ms=8.0)
    out = t.get_search_stats()
    assert out["total"] == 3
    assert out["avg_results"] == pytest.approx((7 + 3 + 5) / 3)
    assert out["max_results"] == 7
    assert out["min_results"] == 3
    assert out["avg_duration_ms"] == pytest.approx((12.0 + 8.0) / 2)
    assert out["click_through_rate"] == pytest.approx(1 / 3)
    assert out["unique_queries"] == 2


def test_crawl_stats_round_trip_via_record_crawl():
    t = _tracker()
    t.record_crawl("https://a", status_code=200, content_size=100,
                   duration_ms=10.0)
    t.record_crawl("https://b", status_code=200, content_size=200,
                   duration_ms=20.0)
    t.record_crawl("https://c", status_code=500, error="boom")
    out = t.get_crawl_stats()
    assert out["total"] == 3
    assert out["avg_duration_ms"] == pytest.approx(15.0)
    assert out["avg_content_size"] == pytest.approx(150.0)
    assert out["total_content_size"] == 300
    assert out["status_codes"] == {200: 2, 500: 1}
    assert out["error_rate"] == pytest.approx(1 / 3)


# --- property check: total invariant --------------------------------------

def test_search_stats_total_property():
    """Property: total always equals the number of recorded search events."""
    t = _tracker()
    for i in range(25):
        t.record_search(f"q{i % 7}", result_count=i, duration_ms=i * 1.0)
    assert t.get_search_stats()["total"] == len(t._search_events) == 25


def test_crawl_stats_total_property():
    t = _tracker()
    for i in range(25):
        t.record_crawl(f"https://h{i}", status_code=200 + (i % 3),
                       content_size=i, duration_ms=i * 1.0)
    out = t.get_crawl_stats()
    assert out["total"] == len(t._crawl_events) == 25
    assert sum(out["status_codes"].values()) == 25


# --- end-to-end CLI run ----------------------------------------------------

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
