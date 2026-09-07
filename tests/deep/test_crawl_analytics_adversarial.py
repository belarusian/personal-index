"""Adversarial deep tests for AnalyticsTracker._compute_crawl_analytics.

Contract source: personal_index/analytics.py docstring (exact contract merged
via #999, ARCH-6). These tests pin the documented behavior against adversarial
inputs: empty event list (guard path), zero/negative durations, top_n
out-of-range, empty/None domains, the independent success/error predicates,
the guarantee that search fields are never touched, and purity (no mutation of
``_crawl_events``).
"""

from __future__ import annotations


import copy

import pytest

from personal_index.analytics import AnalyticsTracker, CrawlEvent


def _tracker() -> AnalyticsTracker:
    return AnalyticsTracker()


def _crawl(url: str, status_code: int = 200, duration_ms: float = 0.0,
           error: str | None = None) -> CrawlEvent:
    return CrawlEvent(url=url, status_code=status_code, duration_ms=duration_ms,
                      error=error)


# --- Guard path: empty event list -----------------------------------------

def test_empty_events_guard_path():
    """Empty _crawl_events -> all four crawl fields stay at defaults."""
    t = _tracker()
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_crawls == 0
    assert data.avg_crawl_duration_ms == 0.0
    assert data.top_domains == []
    assert data.success_count == 0
    assert data.error_count == 0


def test_empty_events_search_fields_untouched():
    """Crawl computation must not touch search fields (stay at defaults)."""
    t = _tracker()
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_searches == 0
    assert data.avg_search_duration_ms == 0.0
    assert data.top_queries == []
    assert data.hourly_searches == {}
    assert data.daily_searches == {}


# --- total_crawls always equals len(events) -------------------------------

def test_total_crawls_equals_event_count():
    t = _tracker()
    for i in range(7):
        t.record_crawl(f"https://a.com/{i}")
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_crawls == 7


# --- avg_crawl_duration_ms: only > 0 durations count ----------------------

def test_avg_duration_excludes_zero_and_negative():
    t = _tracker()
    t.record_crawl("https://a.com/1", duration_ms=100.0)
    t.record_crawl("https://a.com/2", duration_ms=0.0)
    t.record_crawl("https://a.com/3", duration_ms=-50.0)
    t.record_crawl("https://a.com/4", duration_ms=300.0)
    data = t._compute_crawl_analytics(top_n=10)
    # mean of [100, 300] = 200 (0.0 and -50.0 excluded)
    assert data.avg_crawl_duration_ms == pytest.approx(200.0)


def test_avg_duration_all_zero_stays_zero():
    t = _tracker()
    t.record_crawl("https://a.com/1", duration_ms=0.0)
    t.record_crawl("https://a.com/2", duration_ms=0.0)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.avg_crawl_duration_ms == 0.0


def test_avg_duration_all_negative_stays_zero():
    t = _tracker()
    t.record_crawl("https://a.com/1", duration_ms=-1.0)
    t.record_crawl("https://a.com/2", duration_ms=-2.0)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.avg_crawl_duration_ms == 0.0


def test_avg_duration_mixed_with_counts():
    """avg uses only >0 durations while counts use all events."""
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, duration_ms=10.0)
    t.record_crawl("https://a.com/2", status_code=500, duration_ms=0.0)
    t.record_crawl("https://a.com/3", status_code=200, duration_ms=30.0)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_crawls == 3
    assert data.avg_crawl_duration_ms == pytest.approx(20.0)
    assert data.success_count == 2
    assert data.error_count == 1


# --- top_domains: Counter.most_common(top_n), None domains skipped --------

def test_top_domains_most_common_ordering():
    t = _tracker()
    t.record_crawl("https://a.com/x")
    t.record_crawl("https://a.com/y")
    t.record_crawl("https://b.com/z")
    data = t._compute_crawl_analytics(top_n=10)
    assert data.top_domains[0] == ("a.com", 2)
    assert ("b.com", 1) in data.top_domains


def test_top_domains_truncates_to_top_n():
    t = _tracker()
    for d in ("a.com", "b.com", "c.com"):
        t.record_crawl(f"https://{d}/x")
    data = t._compute_crawl_analytics(top_n=2)
    assert len(data.top_domains) == 2


def test_top_domains_top_n_zero_returns_empty():
    t = _tracker()
    t.record_crawl("https://a.com/x")
    t.record_crawl("https://b.com/y")
    data = t._compute_crawl_analytics(top_n=0)
    assert data.top_domains == []


def test_top_domains_top_n_negative_returns_empty():
    """most_common(negative) -> [] (Counter contract)."""
    t = _tracker()
    t.record_crawl("https://a.com/x")
    t.record_crawl("https://b.com/y")
    data = t._compute_crawl_analytics(top_n=-3)
    assert data.top_domains == []


def test_top_domains_top_n_larger_than_distinct():
    t = _tracker()
    t.record_crawl("https://a.com/x")
    t.record_crawl("https://b.com/y")
    data = t._compute_crawl_analytics(top_n=100)
    assert len(data.top_domains) == 2


def test_top_domains_empty_url_skipped():
    """_extract_domain('') -> None -> skipped, not counted."""
    t = _tracker()
    t.record_crawl("")
    t.record_crawl("https://a.com/x")
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_crawls == 2
    assert data.top_domains == [("a.com", 1)]


def test_top_domains_none_url_skipped():
    """url=None -> _extract_domain returns None -> skipped."""
    t = _tracker()
    t._crawl_events.append(_crawl(None, status_code=200))  # type: ignore[arg-type]
    t.record_crawl("https://a.com/x")
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_crawls == 2
    assert data.top_domains == [("a.com", 1)]


def test_top_domains_all_none_domains_empty():
    t = _tracker()
    t.record_crawl("")
    t.record_crawl("")
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_crawls == 2
    assert data.top_domains == []


def test_top_domains_unicode():
    t = _tracker()
    t.record_crawl("https://пример.рф/x")
    t.record_crawl("https://пример.рф/y")
    data = t._compute_crawl_analytics(top_n=10)
    assert data.top_domains[0] == ("пример.рф", 2)


# --- success_count: 200 <= status_code < 400 ------------------------------

def test_success_count_range():
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200)
    t.record_crawl("https://a.com/2", status_code=301)
    t.record_crawl("https://a.com/3", status_code=399)
    t.record_crawl("https://a.com/4", status_code=199)
    t.record_crawl("https://a.com/5", status_code=400)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.success_count == 3


def test_success_count_status_zero_not_success():
    """status_code=0 (CrawlEvent default) is not in [200,400) -> not success."""
    t = _tracker()
    t._crawl_events.append(_crawl("https://a.com/1", status_code=0))
    data = t._compute_crawl_analytics(top_n=10)
    assert data.success_count == 0
    assert data.error_count == 0


# --- error_count: status_code >= 400 OR truthy error ----------------------

def test_error_count_status_ge_400():
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=404)
    t.record_crawl("https://a.com/2", status_code=500)
    t.record_crawl("https://a.com/3", status_code=200)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.error_count == 2


def test_error_count_truthy_error():
    """A truthy error marks the event an error even with a 2xx status."""
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, error="timeout")
    t.record_crawl("https://a.com/2", status_code=200, error=None)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.error_count == 1


def test_error_count_empty_string_error_not_error():
    """error='' is falsy -> not counted as error."""
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, error="")
    data = t._compute_crawl_analytics(top_n=10)
    assert data.error_count == 0


def test_error_and_success_independent_both_counted():
    """2xx status AND truthy error -> counted in BOTH success and error."""
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, error="partial")
    data = t._compute_crawl_analytics(top_n=10)
    assert data.success_count == 1
    assert data.error_count == 1


def test_error_and_success_independent_4xx():
    """4xx status with no error -> error only, not success."""
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=404)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.success_count == 0
    assert data.error_count == 1


# --- search fields untouched on the normal path ---------------------------

def test_search_fields_untouched_normal_path():
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, duration_ms=10.0)
    t.record_crawl("https://a.com/2", status_code=500, duration_ms=20.0)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_searches == 0
    assert data.avg_search_duration_ms == 0.0
    assert data.top_queries == []
    assert data.hourly_searches == {}
    assert data.daily_searches == {}


# --- purity: no mutation of _crawl_events ---------------------------------

def test_purity_no_mutation_of_crawl_events():
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, duration_ms=10.0)
    t.record_crawl("https://a.com/2", status_code=500, duration_ms=0.0)
    before = copy.deepcopy(t._crawl_events)
    t._compute_crawl_analytics(top_n=10)
    t._compute_crawl_analytics(top_n=3)
    assert t._crawl_events == before


def test_idempotence_repeated_calls():
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, duration_ms=10.0)
    t.record_crawl("https://a.com/2", status_code=500, duration_ms=20.0)
    d1 = t._compute_crawl_analytics(top_n=10)
    d2 = t._compute_crawl_analytics(top_n=10)
    assert d1.total_crawls == d2.total_crawls
    assert d1.avg_crawl_duration_ms == d2.avg_crawl_duration_ms
    assert d1.top_domains == d2.top_domains
    assert d1.success_count == d2.success_count
    assert d1.error_count == d2.error_count


def test_returns_fresh_instance_each_call():
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200)
    d1 = t._compute_crawl_analytics(top_n=10)
    d2 = t._compute_crawl_analytics(top_n=10)
    assert d1 is not d2


# --- end-to-end: record then compute --------------------------------------

def test_end_to_end_record_then_compute():
    t = _tracker()
    t.record_crawl("https://a.com/1", status_code=200, duration_ms=100.0)
    t.record_crawl("https://a.com/2", status_code=200, duration_ms=200.0)
    t.record_crawl("https://b.com/3", status_code=404, duration_ms=0.0)
    data = t._compute_crawl_analytics(top_n=10)
    assert data.total_crawls == 3
    assert data.avg_crawl_duration_ms == pytest.approx(150.0)
    assert data.top_domains[0] == ("a.com", 2)
    assert data.success_count == 2
    assert data.error_count == 1


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
