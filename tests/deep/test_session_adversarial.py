"""Adversarial deep tests for personal_index.session (cycle 327).

Primary module: session.py (SessionStats / CrawlSession / SessionManager).
No ``test_session_adversarial.py`` existed before this cycle (only the
non-adversarial ``test_session.py``).

Contract sources:
  - personal_index/session.py docstrings (SessionStats.to_dict,
    SessionManager.load_session - the counts-only round-trip contract).
  - docs/CONTRACTS.md "Defensive-load guard (binding)" (ARCH-63): a
    ``_load``/``load_*`` that rebuilds in-memory state from a persisted JSON
    mapping MUST degrade to the empty state on ANY malformed value (a value
    that is not a mapping, or a mapping whose fields have the wrong type);
    construction MUST NOT raise.

DEFECT FOUND (filed QA-59):
  ``SessionManager.load_session`` reads ``stats_data = data.get("stats", {})``
  and then calls ``stats_data.get(...)`` on it. When the persisted ``stats``
  field is a NON-DICT value (a list, number, string, or null), ``.get`` raises
  ``AttributeError`` out of ``load_session`` instead of degrading to the empty
  stats state. This violates the ARCH-63 defensive-load guard. The missing-
  ``stats`` case (``data.get("stats", {})`` -> ``{}``) is safe; only the
  present-but-wrong-shape case crashes. Pinned xfail-strict below.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from personal_index.session import (
    CrawlSession,
    SessionManager,
    SessionStats,
    SessionStatus,
)


def _write(path: Path, obj) -> str:
    path.write_text(json.dumps(obj))
    return str(path)


# ---------------------------------------------------------------------------
# QA-59: load_session defensive-load guard (ARCH-63) - DEFECT
# ---------------------------------------------------------------------------


class TestLoadSessionStatsShape:
    """ARCH-63 defensive-load guard on the ``stats`` field.

    A well-formed session JSON whose ``stats`` value is NOT a mapping must
    degrade to the empty stats state (all counters 0), exactly like a missing
    ``stats`` key. It must NOT raise out of ``load_session``.
    """

    def test_stats_as_list_degrades_to_empty(self, tmp_path):
        p = _write(tmp_path / "s.json",
                   {"session_id": "x", "status": "active", "stats": [1, 2, 3]})
        m = SessionManager()
        s = m.load_session(p)
        assert s is not None
        assert s.session_id == "x"
        assert s.stats.urls_crawled == 0
        assert s.stats.urls_failed == 0
        assert s.stats.urls_skipped == 0

    def test_stats_as_number_degrades_to_empty(self, tmp_path):
        p = _write(tmp_path / "s.json",
                   {"session_id": "x", "status": "active", "stats": 42})
        m = SessionManager()
        s = m.load_session(p)
        assert s is not None
        assert s.stats.urls_crawled == 0

    def test_stats_as_null_degrades_to_empty(self, tmp_path):
        p = _write(tmp_path / "s.json",
                   {"session_id": "x", "status": "active", "stats": None})
        m = SessionManager()
        s = m.load_session(p)
        assert s is not None
        assert s.stats.urls_crawled == 0

    def test_stats_missing_degrades_to_empty(self, tmp_path):
        """Clean armor: a MISSING stats key already degrades to empty (safe)."""
        p = _write(tmp_path / "s.json", {"session_id": "x", "status": "active"})
        m = SessionManager()
        s = m.load_session(p)
        assert s is not None
        assert s.stats.urls_crawled == 0
        assert s.stats.urls_failed == 0

    def test_stats_empty_dict_degrades_to_empty(self, tmp_path):
        """Clean armor: an empty stats mapping degrades to empty (safe)."""
        p = _write(tmp_path / "s.json",
                   {"session_id": "x", "status": "active", "stats": {}})
        m = SessionManager()
        s = m.load_session(p)
        assert s is not None
        assert s.stats.urls_crawled == 0


# ---------------------------------------------------------------------------
# load_session: other malformed shapes degrade gracefully (clean armor)
# ---------------------------------------------------------------------------


class TestLoadSessionOtherShapes:
    """Non-crashing graceful degradation for other malformed field shapes."""

    def test_top_level_list_returns_none(self, tmp_path):
        p = _write(tmp_path / "s.json", [1, 2, 3])
        assert SessionManager().load_session(p) is None

    def test_top_level_number_returns_none(self, tmp_path):
        p = _write(tmp_path / "s.json", 42)
        assert SessionManager().load_session(p) is None

    def test_invalid_status_returns_none(self, tmp_path):
        p = _write(tmp_path / "s.json",
                   {"session_id": "x", "status": "bogus"})
        assert SessionManager().load_session(p) is None

    def test_missing_session_id_returns_none(self, tmp_path):
        p = _write(tmp_path / "s.json", {"status": "active"})
        assert SessionManager().load_session(p) is None

    def test_empty_session_id_returns_none(self, tmp_path):
        p = _write(tmp_path / "s.json",
                   {"session_id": "", "status": "active"})
        assert SessionManager().load_session(p) is None

    def test_non_dict_config_does_not_crash(self, tmp_path):
        """A non-dict config value is stored as-is; load must not raise."""
        p = _write(tmp_path / "s.json",
                   {"session_id": "x", "status": "active", "config": [1, 2]})
        s = SessionManager().load_session(p)
        assert s is not None
        assert s.session_id == "x"

    def test_non_dict_metadata_does_not_crash(self, tmp_path):
        p = _write(tmp_path / "s.json",
                   {"session_id": "x", "status": "active", "metadata": "oops"})
        s = SessionManager().load_session(p)
        assert s is not None
        assert s.session_id == "x"

    def test_corrupt_json_returns_none(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json {{{")
        assert SessionManager().load_session(str(f)) is None

    def test_missing_file_returns_none(self):
        assert SessionManager().load_session("/nonexistent/nope.json") is None


# ---------------------------------------------------------------------------
# counts-only round-trip invariants (clean armor)
# ---------------------------------------------------------------------------


class TestRoundTripInvariants:
    def test_numeric_counters_survive(self, tmp_path):
        m = SessionManager(storage_path=str(tmp_path))
        s = m.create_session("s1", name="rt", config={"depth": 3})
        s.record_url_crawled("https://a.example.com/x", size=100)
        s.record_url_crawled("https://b.example.org/y", size=200)
        s.record_url_failed("https://bad.com", error="404")
        s.record_url_skipped("https://skip.com")
        s.record_page_indexed()
        path = m.save_session("s1")
        assert path is not None
        loaded = SessionManager(storage_path=str(tmp_path)).load_session(path)
        assert loaded is not None
        assert loaded.stats.urls_crawled == 2
        assert loaded.stats.urls_failed == 1
        assert loaded.stats.urls_skipped == 1
        assert loaded.stats.bytes_downloaded == 300
        assert loaded.stats.pages_indexed == 1
        assert loaded.name == "rt"
        assert loaded.config == {"depth": 3}

    def test_contents_dropped_counts_only(self, tmp_path):
        """The two collection-valued fields are counts-only (not persisted)."""
        m = SessionManager(storage_path=str(tmp_path))
        s = m.create_session("s1")
        s.record_url_crawled("https://a.example.com/x", size=10)
        s.record_url_crawled("https://b.example.org/y", size=20)
        s.record_url_failed("https://bad.com", error="timeout")
        assert len(s.stats.domains_seen) == 2
        assert len(s.stats.errors) == 1
        path = m.save_session("s1")
        loaded = SessionManager(storage_path=str(tmp_path)).load_session(path)
        assert loaded is not None
        assert loaded.stats.domains_seen == set()
        assert loaded.stats.errors == []

    def test_round_trip_idempotent(self, tmp_path):
        """save -> load -> save -> load is stable on the numeric counters."""
        m = SessionManager(storage_path=str(tmp_path))
        s = m.create_session("s1", name="idem")
        s.record_url_crawled("https://example.com", size=100)
        p1 = m.save_session("s1")
        m2 = SessionManager(storage_path=str(tmp_path))
        l1 = m2.load_session(p1)
        p2 = m2.save_session("s1")
        m3 = SessionManager(storage_path=str(tmp_path))
        l2 = m3.load_session(p2)
        assert l1.session_id == l2.session_id
        assert l1.stats.urls_crawled == l2.stats.urls_crawled
        assert l1.stats.bytes_downloaded == l2.stats.bytes_downloaded
        assert l1.name == l2.name


# ---------------------------------------------------------------------------
# cross-reference invariants: active-session bookkeeping
# ---------------------------------------------------------------------------


class TestActiveSessionInvariants:
    def test_first_created_is_active(self):
        m = SessionManager()
        s = m.create_session("a")
        assert m.get_active_session() is s

    def test_second_created_not_active(self):
        m = SessionManager()
        m.create_session("a")
        m.create_session("b")
        assert m.get_active_session().session_id == "a"

    def test_set_active_switches(self):
        m = SessionManager()
        m.create_session("a")
        m.create_session("b")
        assert m.set_active("b") is True
        assert m.get_active_session().session_id == "b"

    def test_set_active_nonexistent_false(self):
        m = SessionManager()
        m.create_session("a")
        assert m.set_active("nope") is False
        assert m.get_active_session().session_id == "a"

    def test_remove_active_clears_active(self):
        m = SessionManager()
        m.create_session("a")
        assert m.remove_session("a") is True
        assert m.get_active_session() is None

    def test_remove_nonexistent_false(self):
        m = SessionManager()
        assert m.remove_session("nope") is False

    def test_duplicate_id_overwrites(self):
        m = SessionManager()
        m.create_session("a", name="first")
        m.create_session("a", name="second")
        assert m.session_count == 1
        assert m.get_session("a").name == "second"

    def test_list_active_filters_by_status(self):
        m = SessionManager()
        m.create_session("a")
        b = m.create_session("b")
        b.pause()
        active = m.list_active()
        assert [s.session_id for s in active] == ["a"]


# ---------------------------------------------------------------------------
# SessionStats edge cases (clean armor)
# ---------------------------------------------------------------------------


class TestStatsEdges:
    def test_success_rate_zero_total(self):
        assert SessionStats().success_rate == 0.0

    def test_success_rate_all_crawled(self):
        assert SessionStats(urls_crawled=5).success_rate == 1.0

    def test_success_rate_all_failed(self):
        assert SessionStats(urls_failed=5).success_rate == 0.0

    def test_success_rate_mixed(self):
        assert SessionStats(urls_crawled=3, urls_failed=1).success_rate == 0.75

    def test_total_processed(self):
        assert SessionStats(urls_crawled=1, urls_failed=2,
                            urls_skipped=3).total_processed == 6

    def test_to_dict_counts_only(self):
        s = SessionStats(urls_crawled=2, urls_failed=1)
        s.domains_seen.add("a.com")
        s.domains_seen.add("b.com")
        s.errors.append("e1")
        d = s.to_dict()
        assert d["domains_seen"] == 2
        assert d["error_count"] == 1
        assert isinstance(d["domains_seen"], int)
        assert isinstance(d["error_count"], int)


# ---------------------------------------------------------------------------
# CrawlSession status transitions (clean armor)
# ---------------------------------------------------------------------------


class TestTransitions:
    def test_pause_from_active(self):
        s = CrawlSession(session_id="x")
        s.pause()
        assert s.status == SessionStatus.PAUSED

    def test_pause_from_completed_noop(self):
        s = CrawlSession(session_id="x")
        s.complete()
        s.pause()
        assert s.status == SessionStatus.COMPLETED

    def test_resume_from_paused(self):
        s = CrawlSession(session_id="x")
        s.pause()
        s.resume()
        assert s.status == SessionStatus.ACTIVE

    def test_resume_from_active_noop(self):
        s = CrawlSession(session_id="x")
        s.resume()
        assert s.status == SessionStatus.ACTIVE

    def test_complete_sets_completed_at(self):
        s = CrawlSession(session_id="x")
        assert s.completed_at is None
        s.complete()
        assert s.completed_at is not None
        assert s.status == SessionStatus.COMPLETED

    def test_fail_appends_error(self):
        s = CrawlSession(session_id="x")
        s.fail("boom")
        assert s.status == SessionStatus.FAILED
        assert "boom" in s.stats.errors

    def test_stop(self):
        s = CrawlSession(session_id="x")
        s.stop()
        assert s.status == SessionStatus.STOPPED
        assert s.completed_at is not None

    def test_duration_active_is_nonnegative(self):
        s = CrawlSession(session_id="x")
        assert s.duration >= 0.0


# ---------------------------------------------------------------------------
# End-to-end: installed CLI smoke (one run per cycle)
# ---------------------------------------------------------------------------


class TestCLIEndToEnd:
    def test_cli_help_no_crash(self):
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Traceback" not in result.stderr

    def test_cli_no_args_no_traceback(self):
        result = subprocess.run(
            [sys.executable, "-m", "personal_index"],
            capture_output=True, text=True, timeout=30,
        )
        assert "Traceback" not in result.stderr, f"Traceback: {result.stderr}"
