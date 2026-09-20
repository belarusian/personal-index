"""Adversarial deep tests for AnalyticsTracker.save / load / clear.

Contract source: personal_index/analytics.py docstrings for save, load and
clear (lines ~358-418). These tests pin the documented persistence behavior
against adversarial inputs: save->load round-trip preserving events exactly,
load of a missing path returning 0, load of malformed / non-dict JSON
returning 0, clear emptying state and a subsequent save writing an empty
store, load idempotence, save returning the path string, no cross-
contamination between search and crawl events on round-trip, and one
end-to-end CLI run (init + stats --format json after a save/load cycle).
"""

from __future__ import annotations

import json


from personal_index.analytics import AnalyticsTracker, CrawlEvent, SearchEvent

TS = "2026-09-06T00:00:00+00:00"


def _tracker() -> AnalyticsTracker:
    return AnalyticsTracker()


def _search(query: str, result_count: int = 0, clicked_url: str | None = None,
            duration_ms: float = 0.0) -> SearchEvent:
    return SearchEvent(query=query, timestamp=TS, result_count=result_count,
                       clicked_url=clicked_url, duration_ms=duration_ms)


def _crawl(url: str, status_code: int = 200, content_size: int = 0,
           duration_ms: float = 0.0, error: str | None = None) -> CrawlEvent:
    return CrawlEvent(url=url, timestamp=TS, status_code=status_code,
                      content_size=content_size, duration_ms=duration_ms,
                      error=error)


def _events_equal(a: list, b: list) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if (x.query, x.timestamp, x.result_count, x.clicked_url, x.duration_ms) != \
           (y.query, y.timestamp, y.result_count, y.clicked_url, y.duration_ms):
            return False
    return True


def _crawls_equal(a: list, b: list) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if (x.url, x.timestamp, x.status_code, x.content_size, x.duration_ms, x.error) != \
           (y.url, y.timestamp, y.status_code, y.content_size, y.duration_ms, y.error):
            return False
    return True


# --- save returns the path string -----------------------------------------

def test_save_returns_path_string(tmp_path):
    """save() returns exactly the path it was given (str)."""
    t = _tracker()
    t.record_search("hello")
    p = str(tmp_path / "store.json")
    out = t.save(p)
    assert out == p
    assert isinstance(out, str)


# --- save -> load round-trip preserves events exactly ---------------------

def test_round_trip_preserves_events_exactly(tmp_path):
    """save then load reproduces every field of every event, in order."""
    t = _tracker()
    t.record_search("alpha", result_count=3, clicked_url="https://a.example",
                    duration_ms=12.5)
    t.record_search("beta", result_count=0, clicked_url=None, duration_ms=0.0)
    t.record_crawl("https://a.example", status_code=200, content_size=1024,
                   duration_ms=7.0, error=None)
    t.record_crawl("https://b.example", status_code=404, content_size=0,
                   duration_ms=1.0, error="not found")

    p = str(tmp_path / "store.json")
    t.save(p)

    t2 = _tracker()
    n = t2.load(p)
    assert n == 4

    assert _events_equal(t._search_events, t2._search_events)
    assert _crawls_equal(t._crawl_events, t2._crawl_events)


def test_round_trip_preserves_unicode_and_edge_strings(tmp_path):
    """Unicode queries/urls and empty/whitespace strings survive a round-trip."""
    t = _tracker()
    t.record_search("café ☕", result_count=1)
    t.record_search("", result_count=0)
    t.record_search("   ", result_count=2)
    t.record_crawl("https://ünïcode.example/путь", status_code=200)

    p = str(tmp_path / "store.json")
    t.save(p)
    t2 = _tracker()
    assert t2.load(p) == 4
    assert _events_equal(t._search_events, t2._search_events)
    assert _crawls_equal(t._crawl_events, t2._crawl_events)


# --- load of a missing path returns 0 -------------------------------------

def test_load_missing_path_returns_zero(tmp_path):
    """load() of a path that does not exist returns 0 (documented guard)."""
    t = _tracker()
    t.record_search("seed")
    assert t.load(str(tmp_path / "does-not-exist.json")) == 0
    # guard must not clobber existing state
    assert len(t._search_events) == 1


# --- load of malformed / non-dict JSON returns 0 --------------------------

def test_load_malformed_json_returns_zero(tmp_path):
    """load() of a file that is not valid JSON returns 0."""
    p = tmp_path / "bad.json"
    p.write_text("{ this is not json", encoding="utf-8")
    t = _tracker()
    t.record_search("seed")
    assert t.load(str(p)) == 0
    assert len(t._search_events) == 1


def test_load_non_dict_json_returns_zero(tmp_path):
    """load() of a top-level JSON array (not a dict) returns 0."""
    p = tmp_path / "arr.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    t = _tracker()
    assert t.load(str(p)) == 0


def test_load_empty_file_returns_zero(tmp_path):
    """load() of an empty file (JSONDecodeError) returns 0."""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    t = _tracker()
    assert t.load(str(p)) == 0


# --- clear empties state; subsequent save writes an empty store -----------

def test_clear_then_save_writes_empty_store(tmp_path):
    """clear() empties both lists; a following save writes an empty store."""
    t = _tracker()
    t.record_search("x")
    t.record_crawl("https://x.example")
    t.clear()
    assert t._search_events == []
    assert t._crawl_events == []

    p = str(tmp_path / "empty-store.json")
    t.save(p)
    data = json.loads((tmp_path / "empty-store.json").read_text(encoding="utf-8"))
    assert data == {"search_events": [], "crawl_events": []}

    t2 = _tracker()
    assert t2.load(p) == 0


# --- load is idempotent ----------------------------------------------------

def test_load_is_idempotent(tmp_path):
    """Loading the same file twice yields identical state and count."""
    t = _tracker()
    t.record_search("q1", result_count=2)
    t.record_crawl("https://q1.example", status_code=200, content_size=5)
    p = str(tmp_path / "store.json")
    t.save(p)

    t2 = _tracker()
    first = t2.load(p)
    snap_search = [vars(e) for e in t2._search_events]
    snap_crawl = [vars(e) for e in t2._crawl_events]
    second = t2.load(p)
    assert first == second == 2
    assert [vars(e) for e in t2._search_events] == snap_search
    assert [vars(e) for e in t2._crawl_events] == snap_crawl


# --- load replaces state, does not append ---------------------------------

def test_load_replaces_prior_state(tmp_path):
    """load() clears existing events before loading (no accumulation)."""
    t = _tracker()
    t.record_search("stale")
    t.record_crawl("https://stale.example")

    t2 = _tracker()
    t2.record_search("fresh", result_count=9)
    p = str(tmp_path / "fresh.json")
    t2.save(p)

    n = t.load(p)
    assert n == 1
    assert len(t._search_events) == 1
    assert t._search_events[0].query == "fresh"
    assert t._crawl_events == []


# --- no cross-contamination between search and crawl events ---------------

def test_no_cross_contamination_on_round_trip(tmp_path):
    """Search events stay in search_events, crawl events in crawl_events."""
    t = _tracker()
    t.record_search("only-search", result_count=4)
    t.record_crawl("https://only-crawl.example", status_code=500, error="boom")

    p = str(tmp_path / "store.json")
    t.save(p)
    t2 = _tracker()
    t2.load(p)

    assert len(t2._search_events) == 1
    assert len(t2._crawl_events) == 1
    assert t2._search_events[0].query == "only-search"
    assert t2._crawl_events[0].url == "https://only-crawl.example"
    # a search event must not have leaked into the crawl list or vice versa
    assert all(isinstance(e, SearchEvent) for e in t2._search_events)
    assert all(isinstance(e, CrawlEvent) for e in t2._crawl_events)


# --- end-to-end CLI run after a save/load cycle ---------------------------

def test_end_to_end_cli_init_and_stats_after_persistence(tmp_path):
    """End-to-end: init + stats --format json, plus a save/load persistence
    cycle through the tracker, all in one run."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    # persistence cycle through the tracker
    t = _tracker()
    t.record_search("cli-query", result_count=2)
    t.record_crawl("https://cli.example", status_code=200, content_size=10)
    p = str(tmp_path / "analytics.json")
    t.save(p)
    t2 = _tracker()
    assert t2.load(p) == 2
    assert _events_equal(t._search_events, t2._search_events)
    assert _crawls_equal(t._crawl_events, t2._crawl_events)

    r = runner.invoke(main, ["stats", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["indexed_pages"] == 0
    assert payload["interests"] == 0
    assert payload["total_tags"] == 0
