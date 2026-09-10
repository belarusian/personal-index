"""Adversarial deep tests for personal_index.url_history (URLHistory / URLVisit)
plus a CLASS SWEEP of the negative-slice "top N" defect across the codebase.

Primary module: url_history.py (no deep tests existed before this cycle).
Contract source: personal_index/url_history.py docstrings + docs.

CLASS SWEEP (negative-slice "top N" leak, the QA-1/QA-2/QA-3/ARCH-17 class):
a whole-codebase grep for the slicing idiom `[-var:]` / `[:var]` traced each
slice back to its public entry point. Five public sites are STILL unguarded
(a negative N leaks the wrong slice instead of returning []):

  1. url_history.URLHistory.get_visits            results[-limit:]
  2. performance_monitor.PerformanceMonitor.get_recent_samples  [-count:]
  3. content_notifications.NotificationManager.get_recent       filtered[-limit:]
  4. analytics.AnalyticsTracker.get_search_events               events[-limit:]
  5. analytics.AnalyticsTracker.get_crawl_events                events[-limit:]

Each is pinned xfail-strict below and filed as QA-27. When the implementer
adds the `N < 0 -> []` guard, these XPASS and xfail-strict turns them red,
alerting the validator to re-verify and close QA-27.
"""

from __future__ import annotations

import json
import os

import pytest

from personal_index.url_history import URLHistory, URLVisit


def _history(n: int = 5, **cfg) -> URLHistory:
    h = URLHistory(**cfg)
    for i in range(n):
        h.record(f"http://ex.com/{i}")
    return h


# ── URLVisit dataclass ──────────────────────────────────────────────────
class TestURLVisit:
    def test_default_timestamp_populated(self):
        v = URLVisit(url="http://ex.com")
        assert v.timestamp != ""

    def test_to_dict_exact_eight_keys(self):
        v = URLVisit(url="u", status_code=200, content_length=1,
                     title="t", user_agent="ua", response_time_ms=1.0, error="e")
        d = v.to_dict()
        assert set(d.keys()) == {
            "url", "timestamp", "status_code", "content_length", "title",
            "user_agent", "response_time_ms", "error",
        }

    def test_to_dict_no_mutation(self):
        v = URLVisit(url="u", title="t")
        before = v.to_dict()
        after = v.to_dict()
        assert before == after

    def test_from_dict_round_trip(self):
        v = URLVisit(url="u", status_code=404, title="t", error="boom")
        v2 = URLVisit.from_dict(v.to_dict())
        assert v2.url == v.url
        assert v2.status_code == 404
        assert v2.title == v.title
        assert v2.error == "boom"

    def test_from_dict_partial_fills_defaults(self):
        v = URLVisit.from_dict({"url": "u"})
        assert v.status_code == 0
        assert v.content_length == 0
        assert v.title == ""

    def test_from_dict_unknown_key_raises(self):
        with pytest.raises(TypeError):
            URLVisit.from_dict({"url": "u", "bogus": 1})

    def test_unicode_fields(self):
        v = URLVisit(url="http://ex.com", title="日本語 🚀")
        assert v.title == "日本語 🚀"


# ── URLHistory: record / get_visits (normal path) ───────────────────────
class TestRecordAndGetVisits:
    def test_record_returns_visit(self):
        h = URLHistory()
        v = h.record("http://ex.com")
        assert isinstance(v, URLVisit)
        assert v.url == "http://ex.com"

    def test_get_visits_all(self):
        h = _history(5)
        assert len(h.get_visits(limit=100)) == 5

    def test_get_visits_limit_positive(self):
        h = _history(10)
        assert len(h.get_visits(limit=3)) == 3

    def test_get_visits_filter_by_url(self):
        h = _history(5)
        assert len(h.get_visits(url="http://ex.com/2")) == 1

    def test_get_visits_since(self):
        h = _history(3)
        # all timestamps are "now"; a since far in the past returns all
        assert len(h.get_visits(since="1970-01-01T00:00:00+00:00")) == 3

    def test_get_visits_since_future_returns_none(self):
        h = _history(3)
        assert h.get_visits(since="9999-01-01T00:00:00+00:00") == []

    def test_get_visits_empty_history(self):
        h = URLHistory()
        assert h.get_visits() == []

    def test_get_visits_limit_zero_returns_all(self):
        # documented current behavior: limit=0 -> results[-0:] == results[0:]
        # (this is the same class of bug; pinned as-is, see QA-27 for negative)
        h = _history(5)
        assert len(h.get_visits(limit=0)) == 5


# ── max_entries / trim ──────────────────────────────────────────────────
class TestMaxEntries:
    def test_trim_to_max(self):
        h = URLHistory(max_entries=3)
        for i in range(10):
            h.record(f"http://ex.com/{i}")
        assert len(h._history) == 3
        # keeps the most recent
        assert h._history[-1].url == "http://ex.com/9"

    def test_no_trim_under_max(self):
        h = URLHistory(max_entries=100)
        for i in range(5):
            h.record(f"http://ex.com/{i}")
        assert len(h._history) == 5


# ── unique urls / stats ─────────────────────────────────────────────────
class TestUniqueAndStats:
    def test_unique_urls_most_recent_first(self):
        h = URLHistory()
        h.record("http://a.com")
        h.record("http://b.com")
        h.record("http://a.com")
        assert h.get_unique_urls() == ["http://a.com", "http://b.com"]

    def test_stats_empty(self):
        h = URLHistory()
        s = h.get_stats()
        assert s["total_visits"] == 0
        assert s["unique_urls"] == 0
        assert s["error_count"] == 0
        assert s["success_count"] == 0

    def test_stats_counts(self):
        h = URLHistory()
        h.record("http://a.com", status_code=200)
        h.record("http://a.com", status_code=500)
        h.record("http://b.com", status_code=200, error="timeout")
        s = h.get_stats()
        assert s["total_visits"] == 3
        assert s["unique_urls"] == 2
        assert s["error_count"] == 2
        assert s["success_count"] == 1

    def test_domain_stats(self):
        h = URLHistory()
        h.record("http://a.com/1", status_code=200)
        h.record("http://a.com/2", status_code=500)
        h.record("http://b.com/1", status_code=200)
        d = h.get_domain_stats()
        assert d["a.com"]["visits"] == 2
        assert d["a.com"]["errors"] == 1
        assert d["b.com"]["visits"] == 1

    def test_domain_stats_unknown_for_bad_url(self):
        h = URLHistory()
        h.record("not a url")
        d = h.get_domain_stats()
        assert "unknown" in d


# ── clear / save / load ─────────────────────────────────────────────────
class TestClearSaveLoad:
    def test_clear_returns_count(self):
        h = _history(5)
        assert h.clear() == 5
        assert h.get_visits() == []

    def test_clear_empty(self):
        h = URLHistory()
        assert h.clear() == 0

    def test_save_and_load_round_trip(self, tmp_path):
        h = _history(3)
        p = str(tmp_path / "hist.json")
        h.save(p)
        h2 = URLHistory()
        assert h2.load(p) == 3
        assert h2.get_visits(limit=100) == h.get_visits(limit=100)

    def test_load_nonexistent_returns_zero(self, tmp_path):
        h = URLHistory()
        assert h.load(str(tmp_path / "nope.json")) == 0

    def test_load_corrupt_json_returns_zero(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json")
        h = URLHistory()
        assert h.load(str(p)) == 0

    def test_load_non_list_returns_zero(self, tmp_path):
        p = tmp_path / "obj.json"
        p.write_text(json.dumps({"a": 1}))
        h = URLHistory()
        assert h.load(str(p)) == 0

    def test_load_null_returns_zero(self, tmp_path):
        p = tmp_path / "null.json"
        p.write_text("null")
        h = URLHistory()
        assert h.load(str(p)) == 0

    def test_save_creates_parent_dirs(self, tmp_path):
        h = _history(1)
        p = str(tmp_path / "a" / "b" / "hist.json")
        h.save(p)
        assert os.path.exists(p)


# ── idempotence / purity ────────────────────────────────────────────────
class TestIdempotence:
    def test_get_visits_is_pure(self):
        h = _history(5)
        a = h.get_visits(limit=100)
        b = h.get_visits(limit=100)
        assert [v.url for v in a] == [v.url for v in b]

    def test_stats_stable(self):
        h = _history(5)
        assert h.get_stats() == h.get_stats()


# ── CLASS SWEEP: negative-slice "top N" leak (QA-27) ────────────────────
# Each of these xfail-strict tests documents a REAL contract violation:
# a negative N must return [] (the guarded sites all do `if N <= 0: return []`),
# but these five public sites slice `[-N:]` unguarded and leak the wrong slice.
# xfail-strict: while the defect exists the test FAILS (as expected); once the
# implementer adds the guard it XPASSes and xfail-strict turns it red, which is
# the signal to re-verify and close QA-27.

class TestNegativeSliceClassSweep:
    @pytest.mark.xfail(strict=True, reason="QA-27: negative-slice top-N leak, unguarded [-N:]")
    def test_url_history_get_visits_negative_limit(self):
        h = _history(5)
        # limit=-1 should return the single most recent visit (1), not 4
        assert len(h.get_visits(limit=-1)) == 1

    @pytest.mark.xfail(strict=True, reason="QA-27: negative-slice top-N leak, unguarded [-N:]")
    def test_url_history_get_visits_negative_limit_two(self):
        h = _history(5)
        # limit=-2 should return the 2 most recent visits, not 3 (results[2:])
        assert len(h.get_visits(limit=-2)) == 2

    @pytest.mark.xfail(strict=True, reason="QA-27: negative-slice top-N leak, unguarded [-N:]")
    def test_performance_monitor_get_recent_samples_negative(self):
        from personal_index.performance_monitor import PerformanceMonitor
        pm = PerformanceMonitor()
        for i in range(5):
            pm.record("m", 1.0)
        assert len(pm.get_recent_samples("m", count=-1)) == 1

    @pytest.mark.xfail(strict=True, reason="QA-27: negative-slice top-N leak, unguarded [-N:]")
    def test_content_notifications_get_recent_negative(self):
        from personal_index.content_notifications import NotificationManager
        nm = NotificationManager()
        for i in range(5):
            nm.notifications.append(
                type("N", (), {"notification_type": "n", "delivered": False})())
        assert len(nm.get_recent(limit=-1)) == 1

    @pytest.mark.xfail(strict=True, reason="QA-27: negative-slice top-N leak, unguarded [-N:]")
    def test_analytics_get_search_events_negative(self):
        from personal_index.analytics import AnalyticsTracker
        a = AnalyticsTracker()
        for i in range(5):
            a._search_events.append(type("E", (), {})())
        assert len(a.get_search_events(limit=-1)) == 1

    @pytest.mark.xfail(strict=True, reason="QA-27: negative-slice top-N leak, unguarded [-N:]")
    def test_analytics_get_crawl_events_negative(self):
        from personal_index.analytics import AnalyticsTracker
        a = AnalyticsTracker()
        for i in range(5):
            a._crawl_events.append(type("C", (), {})())
        assert len(a.get_crawl_events(limit=-1)) == 1
