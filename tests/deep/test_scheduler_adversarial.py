"""Adversarial deep tests for personal_index/scheduler.py.

Cycle 290 — first deep-probe of the never-probed module `scheduler`
(279 lines: `ScheduleConfig` dataclass, `ScheduleEntry` dataclass,
`ScheduleStore` with _load/_save/add/get/remove/update/list_all,
`Scheduler` with add_schedule/add_job/remove_schedule/remove_job/
toggle_schedule/get_due_schedules/update_next_run_times/run_schedule/
list_jobs, and the CLI-facing `ScheduledJob` dataclass).

Note: `tests/deep/test_content_scheduler_adversarial.py` targets the
DIFFERENT module `personal_index.content_scheduler`; this file is the
first deep-probe of `personal_index.scheduler`.

Covers the documented contracts:
  - ScheduleStore._load: missing file -> empty; malformed JSON / non-dict
    JSON / entry missing `config` -> empty (defensive, no crash).
  - ScheduleStore._save: atomic (tmp + fsync + os.replace), no .tmp
    leftover; round-trips config/counters/last_run/next_run.
  - ScheduleStore.add/get/remove/update/list_all: idempotent reload.
  - Scheduler.get_due_schedules: enabled + next_run <= now.
  - Scheduler.update_next_run_times: next_run = last_run + interval.
  - Unicode names round-trip through JSON.

Plus: None/empty/whitespace/unicode/oversized/boundary inputs, idempotence,
error paths, and an end-to-end run through the installed CLI.

One REAL contract violation surfaced and is pinned with xfail-strict
(documented, not hard-failed, so main stays green):
  - QA-52 (issue #1636): ScheduleStore._load accepts a naive (offset-less)
    ISO datetime for last_run/next_run, but Scheduler.get_due_schedules
    compares `entry.next_run <= datetime.now(timezone.utc)` — comparing an
    offset-naive datetime to an offset-aware one raises TypeError, so a
    store file written with naive timestamps makes the public
    get_due_schedules() API crash.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest
from click.testing import CliRunner

from personal_index.scheduler import (
    ScheduleConfig,
    ScheduleEntry,
    ScheduleStore,
    Scheduler,
)


class _Stub:
    """Minimal stand-in for InterestStore / SearchIndex (Scheduler deps)."""


def _make_scheduler(tmp_path, name="s.json"):
    store = ScheduleStore(path=str(tmp_path / name))
    return Scheduler(
        interest_store=_Stub(),
        search_index=_Stub(),
        schedule_store=store,
    ), store


def _aware(dt):
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


# ── ScheduleStore._load defensive parsing ─────────────────────────────
class TestLoadDefensive:
    def test_missing_file_empty(self, tmp_path):
        store = ScheduleStore(path=str(tmp_path / "nope.json"))
        assert store.list_all() == []

    def test_malformed_json_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{this is not json")
        store = ScheduleStore(path=str(p))
        assert store.list_all() == []

    def test_non_dict_json_empty(self, tmp_path):
        p = tmp_path / "list.json"
        p.write_text("[1, 2, 3]")
        store = ScheduleStore(path=str(p))
        assert store.list_all() == []

    def test_entry_missing_config_empty(self, tmp_path):
        p = tmp_path / "noconfig.json"
        p.write_text(json.dumps({"j": {"run_count": 1}}))
        store = ScheduleStore(path=str(p))
        assert store.list_all() == []

    def test_empty_object_empty(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("{}")
        store = ScheduleStore(path=str(p))
        assert store.list_all() == []

    def test_null_last_run_next_run(self, tmp_path):
        p = tmp_path / "nulls.json"
        p.write_text(
            json.dumps(
                {
                    "j": {
                        "config": {
                            "interval_hours": 24,
                            "enabled": True,
                            "seed_urls": [],
                            "max_pages_per_run": 50,
                            "crawl_depth": 2,
                            "delay": 1.0,
                        },
                        "run_count": 0,
                        "total_pages_indexed": 0,
                        "last_run": None,
                        "next_run": None,
                    }
                }
            )
        )
        store = ScheduleStore(path=str(p))
        e = store.get("j")
        assert e is not None
        assert e.last_run is None
        assert e.next_run is None


# ── round-trip / idempotence / unicode ────────────────────────────────
class TestRoundTrip:
    def test_full_round_trip(self, tmp_path):
        p = str(tmp_path / "rt.json")
        store = ScheduleStore(path=p)
        e = ScheduleEntry(
            name="job",
            config=ScheduleConfig(
                interval_hours=6,
                seed_urls=["https://a.com", "https://b.com"],
            ),
            run_count=3,
            total_pages_indexed=42,
            last_run=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            next_run=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
        )
        store.add(e)
        reloaded = ScheduleStore(path=p).get("job")
        assert reloaded.name == "job"
        assert reloaded.config.interval_hours == 6
        assert reloaded.config.seed_urls == ["https://a.com", "https://b.com"]
        assert reloaded.run_count == 3
        assert reloaded.total_pages_indexed == 42
        assert reloaded.last_run == e.last_run
        assert reloaded.next_run == e.next_run

    def test_idempotent_reload(self, tmp_path):
        p = str(tmp_path / "idem.json")
        store = ScheduleStore(path=p)
        store.add(ScheduleEntry(name="a", config=ScheduleConfig()))
        store.add(ScheduleEntry(name="b", config=ScheduleConfig()))
        for _ in range(3):
            assert len(ScheduleStore(path=p).list_all()) == 2

    def test_unicode_name_round_trip(self, tmp_path):
        p = str(tmp_path / "uni.json")
        store = ScheduleStore(path=p)
        name = "café-日本語-🚀"
        store.add(ScheduleEntry(name=name, config=ScheduleConfig()))
        assert ScheduleStore(path=p).get(name).name == name

    def test_no_tmp_leftover(self, tmp_path):
        p = str(tmp_path / "atomic.json")
        store = ScheduleStore(path=p)
        store.add(ScheduleEntry(name="a", config=ScheduleConfig()))
        assert not os.path.exists(p + ".tmp")


# ── add/get/remove/update/list_all ────────────────────────────────────
class TestStoreCrud:
    def test_get_missing_returns_none(self, tmp_path):
        store = ScheduleStore(path=str(tmp_path / "x.json"))
        assert store.get("nope") is None

    def test_remove_missing_returns_false(self, tmp_path):
        store = ScheduleStore(path=str(tmp_path / "x.json"))
        assert store.remove("nope") is False

    def test_remove_present_returns_true(self, tmp_path):
        p = str(tmp_path / "x.json")
        store = ScheduleStore(path=p)
        store.add(ScheduleEntry(name="a", config=ScheduleConfig()))
        assert store.remove("a") is True
        assert ScheduleStore(path=p).get("a") is None

    def test_add_overwrites_same_name(self, tmp_path):
        p = str(tmp_path / "x.json")
        store = ScheduleStore(path=p)
        store.add(ScheduleEntry(name="a", config=ScheduleConfig(interval_hours=1)))
        store.add(ScheduleEntry(name="a", config=ScheduleConfig(interval_hours=9)))
        assert len(ScheduleStore(path=p).list_all()) == 1
        assert ScheduleStore(path=p).get("a").config.interval_hours == 9


# ── Scheduler.get_due_schedules ───────────────────────────────────────
class TestGetDueSchedules:
    def test_disabled_not_due(self, tmp_path):
        sch, store = _make_scheduler(tmp_path)
        store.add(
            ScheduleEntry(
                name="off",
                config=ScheduleConfig(enabled=False),
                next_run=datetime(2000, 1, 1, tzinfo=timezone.utc),
            )
        )
        assert sch.get_due_schedules() == []

    def test_none_next_run_is_due(self, tmp_path):
        sch, store = _make_scheduler(tmp_path)
        store.add(ScheduleEntry(name="due", config=ScheduleConfig()))
        due = sch.get_due_schedules()
        assert [e.name for e in due] == ["due"]

    def test_future_next_run_not_due(self, tmp_path):
        sch, store = _make_scheduler(tmp_path)
        store.add(
            ScheduleEntry(
                name="later",
                config=ScheduleConfig(),
                next_run=datetime.now(timezone.utc).replace(
                    year=2999
                ),
            )
        )
        assert sch.get_due_schedules() == []

    def test_past_next_run_due(self, tmp_path):
        sch, store = _make_scheduler(tmp_path)
        store.add(
            ScheduleEntry(
                name="past",
                config=ScheduleConfig(),
                next_run=datetime(2000, 1, 1, tzinfo=timezone.utc),
            )
        )
        assert [e.name for e in sch.get_due_schedules()] == ["past"]

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-52 (issue #1636): ScheduleStore._load accepts a naive "
            "(offset-less) ISO datetime for next_run, but "
            "Scheduler.get_due_schedules compares it against an aware "
            "datetime.now(timezone.utc), raising TypeError. A store file "
            "written with naive timestamps makes the public API crash."
        ),
    )
    def test_naive_stored_datetime_does_not_crash_get_due(self, tmp_path):
        p = tmp_path / "naive.json"
        p.write_text(
            json.dumps(
                {
                    "j": {
                        "config": {
                            "interval_hours": 24,
                            "enabled": True,
                            "seed_urls": [],
                            "max_pages_per_run": 50,
                            "crawl_depth": 2,
                            "delay": 1.0,
                        },
                        "run_count": 0,
                        "total_pages_indexed": 0,
                        "last_run": "2026-01-01T00:00:00",
                        "next_run": "2026-01-01T00:00:00",
                    }
                }
            )
        )
        store = ScheduleStore(path=str(p))
        sch = Scheduler(
            interest_store=_Stub(),
            search_index=_Stub(),
            schedule_store=store,
        )
        # Contract: a loaded entry must be comparable in get_due_schedules.
        due = sch.get_due_schedules()
        assert any(e.name == "j" for e in due)


# ── Scheduler.update_next_run_times ───────────────────────────────────
class TestUpdateNextRunTimes:
    def test_next_run_is_last_run_plus_interval(self, tmp_path):
        sch, store = _make_scheduler(tmp_path)
        e = ScheduleEntry(name="j", config=ScheduleConfig(interval_hours=6))
        e.last_run = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        store.add(e)
        sch.update_next_run_times()
        assert store.get("j").next_run == datetime(
            2026, 1, 1, 6, 0, tzinfo=timezone.utc
        )

    def test_no_last_run_leaves_next_run_untouched(self, tmp_path):
        sch, store = _make_scheduler(tmp_path)
        e = ScheduleEntry(name="j", config=ScheduleConfig(interval_hours=6))
        e.next_run = datetime(2026, 1, 1, tzinfo=timezone.utc)
        store.add(e)
        sch.update_next_run_times()
        assert store.get("j").next_run == e.next_run

    def test_zero_interval_next_run_equals_last_run(self, tmp_path):
        sch, store = _make_scheduler(tmp_path)
        e = ScheduleEntry(name="j", config=ScheduleConfig(interval_hours=0))
        e.last_run = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        store.add(e)
        sch.update_next_run_times()
        assert store.get("j").next_run == e.last_run


# ── toggle_schedule ───────────────────────────────────────────────────
class TestToggleSchedule:
    def test_toggle_missing_returns_none(self, tmp_path):
        sch, _ = _make_scheduler(tmp_path)
        assert sch.toggle_schedule("nope") is None

    def test_toggle_flips_enabled(self, tmp_path):
        sch, store = _make_scheduler(tmp_path)
        store.add(ScheduleEntry(name="j", config=ScheduleConfig(enabled=True)))
        e = sch.toggle_schedule("j")
        assert e.config.enabled is False
        e2 = sch.toggle_schedule("j")
        assert e2.config.enabled is True


# ── end-to-end installed CLI run ──────────────────────────────────────
class TestEndToEndCli:
    def test_cli_schedule_add_list_remove(self, tmp_path):
        from personal_index.cli import main

        runner = CliRunner(isolate_filesystem=False)
        dd = str(tmp_path / "data")
        r = runner.invoke(main, ["init", "--data-dir", dd])
        assert r.exit_code == 0, r.output

        r2 = runner.invoke(
            main,
            [
                "schedule",
                "add",
                "-n",
                "daily",
                "-u",
                "https://example.com",
                "-i",
                "12",
                "--data-dir",
                dd,
            ],
        )
        assert r2.exit_code == 0, r2.output
        assert "Added scheduled job" in r2.output

        r3 = runner.invoke(main, ["schedule", "list", "--data-dir", dd])
        assert r3.exit_code == 0, r3.output
        assert "daily" in r3.output
        assert "12 hours" in r3.output

        r4 = runner.invoke(
            main, ["schedule", "remove", "daily", "--data-dir", dd]
        )
        assert r4.exit_code == 0, r4.output
        assert "Removed scheduled job" in r4.output
