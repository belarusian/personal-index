"""Adversarial deep tests for personal_index.scheduler (ARCH-104 atomic-save contract).

Targets the ScheduleStore persistence contract:
  - _save is ATOMIC (temp + fsync + os.replace): a crash mid-write must leave the
    previous complete file intact (ARCH-104 fix).
  - _load degradation is INTENTIONAL and documented (docs/scheduler.md): absent /
    corrupt / non-dict / any-entry-missing-key / unparseable-timestamp files all
    silently reset to empty. These pins document the documented behavior.
  - round-trip, idempotence, unicode, empty/whitespace guards.
  - one end-to-end run through the installed CLI (schedule add/list/remove).

Validator-owned (tests/deep/**). No product code is modified here.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from personal_index.scheduler import (
    ScheduleConfig,
    ScheduleEntry,
    ScheduleStore,
)


def _cfg(
    interval_hours: int = 24,
    enabled: bool = True,
    seed_urls: list[str] | None = None,
    max_pages_per_run: int = 50,
    crawl_depth: int = 2,
    delay: float = 1.0,
) -> ScheduleConfig:
    return ScheduleConfig(
        interval_hours=interval_hours,
        enabled=enabled,
        seed_urls=list(seed_urls) if seed_urls is not None else [],
        max_pages_per_run=max_pages_per_run,
        crawl_depth=crawl_depth,
        delay=delay,
    )


def _entry(name: str, **cfg_over) -> ScheduleEntry:
    return ScheduleEntry(name=name, config=_cfg(**cfg_over))


# ── ARCH-104: atomic save ──────────────────────────────────────────────


class TestAtomicSave:
    def test_crash_mid_write_leaves_original_intact(self, tmp_path, monkeypatch):
        """A crash during json.dump must NOT truncate the existing file."""
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        store.add(_entry("good", interval_hours=6))
        # capture the complete pre-crash file contents
        with open(p) as f:
            before = f.read()
        assert "good" in before

        # Simulate a crash mid-write: json.dump raises before os.replace runs.
        def _boom(*a, **k):
            raise OSError("simulated crash mid-write")

        monkeypatch.setattr(json, "dump", _boom)
        with pytest.raises(OSError):
            store.add(_entry("second", interval_hours=12))

        # The target file must still hold the previous complete JSON.
        with open(p) as f:
            after = f.read()
        assert after == before
        assert "good" in after
        assert "second" not in after

    def test_roundtrip_after_failed_save(self, tmp_path, monkeypatch):
        """After a failed save, a fresh store loads the pre-failure entries."""
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        store.add(_entry("survivor", interval_hours=3))

        def _boom(*a, **k):
            raise OSError("crash")

        monkeypatch.setattr(json, "dump", _boom)
        with pytest.raises(OSError):
            store.add(_entry("loser"))

        fresh = ScheduleStore(path=p)
        assert [e.name for e in fresh.list_all()] == ["survivor"]
        assert fresh.get("survivor").config.interval_hours == 3
        assert fresh.get("loser") is None

    def test_no_temp_file_left_behind_on_success(self, tmp_path):
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        store.add(_entry("a"))
        assert not os.path.exists(p + ".tmp")


# ── _load degradation (documented intentional behavior) ────────────────


class TestLoadDegradation:
    def test_absent_file_empty(self, tmp_path):
        s = ScheduleStore(path=str(tmp_path / "nope.json"))
        assert s.list_all() == []

    def test_corrupt_json_empty(self, tmp_path):
        p = tmp_path / "s.json"
        p.write_text("{ this is not json ]")
        s = ScheduleStore(path=str(p))
        assert s.list_all() == []

    def test_non_dict_json_empty(self, tmp_path):
        p = tmp_path / "s.json"
        p.write_text("[1, 2, 3]")
        s = ScheduleStore(path=str(p))
        assert s.list_all() == []

    def test_null_json_empty(self, tmp_path):
        p = tmp_path / "s.json"
        p.write_text("null")
        s = ScheduleStore(path=str(p))
        assert s.list_all() == []

    def test_one_bad_config_key_wipes_store(self, tmp_path):
        """Documented: any entry with a missing/unknown key resets the whole store."""
        p = tmp_path / "s.json"
        good = {
            "config": {"interval_hours": 24, "enabled": True, "seed_urls": [],
                       "max_pages_per_run": 50, "crawl_depth": 2, "delay": 1.0},
            "run_count": 1, "total_pages_indexed": 5,
            "last_run": None, "next_run": None,
        }
        bad = dict(good)
        bad["config"] = dict(good["config"], BOGUS_KEY=9)
        p.write_text(json.dumps({"good1": good, "bad": bad}))
        s = ScheduleStore(path=str(p))
        assert s.list_all() == []

    def test_one_bad_last_run_wipes_store(self, tmp_path):
        p = tmp_path / "s.json"
        good = {
            "config": {"interval_hours": 24, "enabled": True, "seed_urls": [],
                       "max_pages_per_run": 50, "crawl_depth": 2, "delay": 1.0},
            "run_count": 1, "total_pages_indexed": 5,
            "last_run": None, "next_run": None,
        }
        bad = dict(good)
        bad["last_run"] = "not-a-date"
        p.write_text(json.dumps({"good1": good, "bad": bad}))
        s = ScheduleStore(path=str(p))
        assert s.list_all() == []


# ── round-trip / idempotence / guards ──────────────────────────────────


class TestRoundTripAndGuards:
    def test_roundtrip_preserves_fields(self, tmp_path):
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        store.add(_entry("job", interval_hours=7, seed_urls=["https://x.com"],
                         crawl_depth=4, max_pages_per_run=99))
        store.add(_entry("job2", interval_hours=1))
        fresh = ScheduleStore(path=p)
        assert {e.name for e in fresh.list_all()} == {"job", "job2"}
        j = fresh.get("job")
        assert j.config.interval_hours == 7
        assert j.config.seed_urls == ["https://x.com"]
        assert j.config.crawl_depth == 4
        assert j.config.max_pages_per_run == 99

    def test_add_same_name_idempotent(self, tmp_path):
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        store.add(_entry("dup", interval_hours=1))
        store.add(_entry("dup", interval_hours=2))
        assert len(store.list_all()) == 1
        assert store.get("dup").config.interval_hours == 2

    def test_remove_absent_returns_false(self, tmp_path):
        s = ScheduleStore(path=str(tmp_path / "s.json"))
        assert s.remove("ghost") is False

    def test_remove_present_returns_true_and_persists(self, tmp_path):
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        store.add(_entry("a"))
        store.add(_entry("b"))
        assert store.remove("a") is True
        fresh = ScheduleStore(path=p)
        assert [e.name for e in fresh.list_all()] == ["b"]

    def test_unicode_name_roundtrip(self, tmp_path):
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        store.add(_entry("название-日本語-🚀"))
        fresh = ScheduleStore(path=p)
        assert [e.name for e in fresh.list_all()] == ["название-日本語-🚀"]

    def test_empty_and_whitespace_name_distinct(self, tmp_path):
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        store.add(_entry(""))
        store.add(_entry("   "))
        assert len(store.list_all()) == 2

    def test_datetime_fields_roundtrip(self, tmp_path):
        p = str(tmp_path / "s.json")
        store = ScheduleStore(path=p)
        e = _entry("dt")
        e.last_run = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        e.next_run = datetime(2026, 1, 3, 3, 4, 5, tzinfo=timezone.utc)
        store.add(e)
        fresh = ScheduleStore(path=p)
        got = fresh.get("dt")
        assert got.last_run == e.last_run
        assert got.next_run == e.next_run


# ── end-to-end CLI run ─────────────────────────────────────────────────


class TestCliEndToEnd:
    def test_schedule_add_list_remove(self, tmp_path):
        from click.testing import CliRunner
        from personal_index.cli import main

        dd = str(tmp_path)
        runner = CliRunner()

        r = runner.invoke(main, ["schedule", "add", "-n", "daily",
                                 "-u", "https://example.com", "-i", "12",
                                 "--data-dir", dd])
        assert r.exit_code == 0, r.output
        assert "Added scheduled job 'daily'" in r.output

        r = runner.invoke(main, ["schedule", "list", "--data-dir", dd])
        assert r.exit_code == 0, r.output
        assert "daily" in r.output
        assert "12 hours" in r.output

        # duplicate add is rejected
        r = runner.invoke(main, ["schedule", "add", "-n", "daily",
                                 "-u", "https://example.com", "--data-dir", dd])
        assert r.exit_code != 0
        assert "already exists" in r.output

        r = runner.invoke(main, ["schedule", "remove", "daily",
                                 "--data-dir", dd])
        assert r.exit_code == 0, r.output
        assert "Removed scheduled job 'daily'" in r.output

        r = runner.invoke(main, ["schedule", "list", "--data-dir", dd])
        assert "No scheduled jobs found." in r.output
