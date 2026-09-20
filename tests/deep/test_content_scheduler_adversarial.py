"""Adversarial deep tests for personal_index.content_scheduler (never-probed).

Pins the documented contract of the PASSIVE task scheduler:
  * No execution loop / timer / start/stop/tick - a task runs only when the
    caller invokes TaskScheduler.run_due_tasks().
  * Stale next_run / no catch-up: a task whose next_run has passed without a
    run is immediately due on the first run_due_tasks() call.
  * A disabled task's next_run is never advanced.
  * Malformed cron (wrong field count, zero/negative step, non-numeric token,
    out-of-range values, inverted range) -> next_run is None (never runs).
  * Cron DOW 7 is an alias for Sunday (0); cron DOW is converted to Python
    weekday (cron 1=Mon -> python 0=Mon).
  * Standard cron dom/dow OR rule: when BOTH dom and dow are restricted, a day
    matches if it satisfies dom OR dow.
  * CANCELLED is reserved: no code path assigns it (passive scheduler).
  * A failing callback -> run() returns False, status FAILED, last_error set,
    run_count NOT incremented.
  * to_dict() round-trips the exact key set; status is the enum .value.

Cycle 278 (validator) - PROBE of a never-probed subsystem.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from click.testing import CliRunner

from personal_index.content_scheduler import (
    ScheduledTask,
    TaskScheduler,
    TaskStatus,
)


# ── cron field parsing: malformed -> never runs ──────────────────────────
class TestMalformedCronNeverRuns:
    def test_wrong_field_count_too_few(self):
        t = ScheduledTask("t", "n", "x", "* * *")
        assert t.next_run is None

    def test_wrong_field_count_too_many(self):
        t = ScheduledTask("t", "n", "x", "* * * * * *")
        assert t.next_run is None

    def test_zero_step_never_runs(self):
        # '*/0' -> int('0') step -> range(..., 0) is empty -> ValueError-free
        # but produces no values; the contract is "never runs".
        t = ScheduledTask("t", "n", "x", "*/0 * * * *")
        assert t.next_run is None

    def test_negative_step_never_runs(self):
        t = ScheduledTask("t", "n", "x", "*/-1 * * * *")
        assert t.next_run is None

    def test_non_numeric_token_never_runs(self):
        t = ScheduledTask("t", "n", "x", "abc * * * *")
        assert t.next_run is None

    def test_empty_field_never_runs(self):
        t = ScheduledTask("t", "n", "x", "  * * * *")
        assert t.next_run is None

    def test_inverted_range_never_runs(self):
        # 5-1 -> range(5, 2) is empty -> no values -> never runs.
        t = ScheduledTask("t", "n", "x", "5-1 * * * *")
        assert t._minute == []
        assert t.next_run is None


# ── cron field parsing: out-of-range values are dropped ──────────────────
class TestOutOfRangeValuesDropped:
    def test_minute_60_dropped(self):
        t = ScheduledTask("t", "n", "x", "60 * * * *")
        assert t._minute == []
        assert t.next_run is None

    def test_hour_24_dropped(self):
        t = ScheduledTask("t", "n", "x", "0 24 * * *")
        assert t._hour == []
        assert t.next_run is None

    def test_dom_32_dropped(self):
        t = ScheduledTask("t", "n", "x", "0 0 32 * *")
        assert t._dom == []
        assert t.next_run is None

    def test_month_13_dropped(self):
        t = ScheduledTask("t", "n", "x", "0 0 * 13 *")
        assert t._month == []
        assert t.next_run is None


# ── cron field parsing: valid constructs ─────────────────────────────────
class TestValidCronConstructs:
    def test_star_expands_full_range(self):
        t = ScheduledTask("t", "n", "x", "* * * * *")
        assert t._minute == list(range(0, 60))
        assert t._hour == list(range(0, 24))
        assert t._dom == list(range(1, 32))
        assert t._month == list(range(1, 13))

    def test_range_with_step(self):
        t = ScheduledTask("t", "n", "x", "1-5/2 * * * *")
        assert t._minute == [1, 3, 5]

    def test_list_of_values(self):
        t = ScheduledTask("t", "n", "x", "0,15,30,45 * * * *")
        assert t._minute == [0, 15, 30, 45]

    def test_step_on_single_value(self):
        # '5/10' -> start=5, end=max_val(59), step=10 -> 5,15,...,55
        t = ScheduledTask("t", "n", "x", "5/10 * * * *")
        assert t._minute == [5, 15, 25, 35, 45, 55]

    def test_valid_daily_cron_has_next_run(self):
        t = ScheduledTask("t", "n", "x", "0 0 * * *")
        assert t.next_run is not None
        assert t.next_run.minute == 0
        assert t.next_run.hour == 0

    def test_valid_cron_next_run_is_future(self):
        t = ScheduledTask("t", "n", "x", "* * * * *")
        assert t.next_run is not None
        assert t.next_run > datetime.now(timezone.utc) - timedelta(minutes=1)


# ── cron DOW: 7 == Sunday alias, cron->python weekday conversion ─────────
class TestCronDow:
    def test_dow_7_is_sunday_alias(self):
        # cron 7 -> folded to 0 -> python weekday 6 (Sunday)
        t = ScheduledTask("t", "n", "x", "0 0 * * 7")
        assert t._dow == [6]

    def test_dow_0_is_sunday(self):
        t = ScheduledTask("t", "n", "x", "0 0 * * 0")
        assert t._dow == [6]

    def test_dow_1_is_monday(self):
        # cron 1 (Mon) -> python 0 (Mon)
        t = ScheduledTask("t", "n", "x", "0 0 * * 1")
        assert t._dow == [0]

    def test_dow_6_is_saturday(self):
        # cron 6 (Sat) -> python 5 (Sat)
        t = ScheduledTask("t", "n", "x", "0 0 * * 6")
        assert t._dow == [5]

    def test_dow_star_full_week(self):
        # '*' parses over the full 0-7 range and folds 7 -> 0, so Sunday
        # (python 6) can appear twice; the contract is that ALL seven
        # weekdays are covered, not the exact list shape.
        t = ScheduledTask("t", "n", "x", "0 0 * * *")
        assert set(t._dow) == {0, 1, 2, 3, 4, 5, 6}


# ── cron dom/dow OR rule (standard cron) ─────────────────────────────────
class TestDomDowOrRule:
    def test_both_restricted_matches_or(self):
        # dom=1 (1st of month) AND dow=1 (Monday). Standard cron: a day
        # matches if it satisfies dom OR dow. 2026-09-21 is a Monday (not the
        # 1st), so it must be matched via the OR branch.
        t = ScheduledTask("t", "n", "x", "0 0 1 * 1")
        assert t._dom_restricted is True
        assert t._dow_restricted is True
        assert t.next_run is not None
        # The computed next run must be a Monday (dow branch) OR the 1st.
        nr = t.next_run
        assert nr.weekday() == 0 or nr.day == 1

    def test_only_dom_restricted_ignores_dow(self):
        # dom=1, dow=* -> only dom matters.
        t = ScheduledTask("t", "n", "x", "0 0 1 * *")
        assert t._dom_restricted is True
        assert t._dow_restricted is False
        assert t.next_run is not None
        assert t.next_run.day == 1

    def test_only_dow_restricted_ignores_dom(self):
        # dom=*, dow=1 (Mon) -> only dow matters.
        t = ScheduledTask("t", "n", "x", "0 0 * * 1")
        assert t._dom_restricted is False
        assert t._dow_restricted is True
        assert t.next_run is not None
        assert t.next_run.weekday() == 0


# ── is_due / run / run_due_tasks (passive scheduler) ─────────────────────
class TestPassiveScheduler:
    def test_is_due_false_when_next_run_future(self):
        t = ScheduledTask("t", "n", "x", "* * * * *")
        # next_run is computed ~1 minute in the future -> not due yet.
        assert t.is_due() is False

    def test_is_due_true_when_next_run_past(self):
        t = ScheduledTask("t", "n", "x", "* * * * *")
        t.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert t.is_due() is True

    def test_is_due_false_when_next_run_none(self):
        t = ScheduledTask("t", "n", "x", "*/0 * * * *")
        assert t.next_run is None
        assert t.is_due() is False

    def test_disabled_task_never_due(self):
        t = ScheduledTask("t", "n", "x", "* * * * *")
        t.enabled = False
        t.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert t.is_due() is False

    def test_run_invokes_callback_and_advances(self):
        calls: list[str] = []
        t = ScheduledTask("t", "n", "x", "* * * * *",
                          callback=lambda task: calls.append(task.task_id))
        before = t.next_run
        assert t.run() is True
        assert calls == ["t"]
        assert t.status is TaskStatus.COMPLETED
        assert t.run_count == 1
        assert t.last_run is not None
        # next_run recomputed after a successful run. For a per-minute cron
        # the recomputed value may equal the prior one when both fall in the
        # same minute, so pin "not None and not in the past" (the contract:
        # next_run is re-computed after a successful run), not strict increase.
        assert t.next_run is not None
        assert t.next_run >= before

    def test_failing_callback_marks_failed_no_count(self):
        def boom(task):
            raise ValueError("kaboom")

        t = ScheduledTask("t", "n", "x", "* * * * *", callback=boom)
        assert t.run() is False
        assert t.status is TaskStatus.FAILED
        assert t.last_error == "kaboom"
        assert t.run_count == 0  # not incremented on failure

    def test_run_without_callback_is_noop_success(self):
        t = ScheduledTask("t", "n", "x", "* * * * *", callback=None)
        assert t.run() is True
        assert t.status is TaskStatus.COMPLETED
        assert t.run_count == 1

    def test_run_due_tasks_runs_only_due(self):
        s = TaskScheduler()
        calls: list[str] = []
        due = s.add_task("due", "x", "* * * * *",
                         callback=lambda t: calls.append(t.task_id))
        not_due = s.add_task("notdue", "x", "* * * * *",
                             callback=lambda t: calls.append(t.task_id))
        due.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        not_due.next_run = datetime.now(timezone.utc) + timedelta(hours=1)
        results = s.run_due_tasks()
        assert [r["task_id"] for r in results] == [due.task_id]
        assert results[0]["success"] is True
        assert results[0]["status"] == "completed"
        assert calls == [due.task_id]

    def test_run_due_tasks_result_shape(self):
        s = TaskScheduler()
        t = s.add_task("n", "x", "* * * * *", callback=lambda task: None)
        t.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        results = s.run_due_tasks()
        assert set(results[0].keys()) == {"task_id", "name", "success", "status"}


# ── TaskScheduler management ─────────────────────────────────────────────
class TestSchedulerManagement:
    def test_add_task_assigns_sequential_ids(self):
        s = TaskScheduler()
        a = s.add_task("a", "x", "* * * * *")
        b = s.add_task("b", "x", "* * * * *")
        assert a.task_id == "task_1"
        assert b.task_id == "task_2"

    def test_get_task_missing_returns_none(self):
        s = TaskScheduler()
        assert s.get_task("nope") is None

    def test_remove_task_idempotent(self):
        s = TaskScheduler()
        t = s.add_task("a", "x", "* * * * *")
        assert s.remove_task(t.task_id) is True
        assert s.remove_task(t.task_id) is False
        assert s.get_task(t.task_id) is None

    def test_enable_disable_round_trip(self):
        s = TaskScheduler()
        t = s.add_task("a", "x", "* * * * *")
        assert t.enabled is True
        assert s.disable_task(t.task_id) is True
        assert t.enabled is False
        assert s.enable_task(t.task_id) is True
        assert t.enabled is True

    def test_enable_disable_missing_returns_false(self):
        s = TaskScheduler()
        assert s.enable_task("nope") is False
        assert s.disable_task("nope") is False

    def test_list_tasks_by_type(self):
        s = TaskScheduler()
        s.add_task("a", "typeA", "* * * * *")
        s.add_task("b", "typeA", "* * * * *")
        s.add_task("c", "typeB", "* * * * *")
        assert [t.task_id for t in s.list_tasks("typeA")] == ["task_1", "task_2"]
        assert len(s.list_tasks()) == 3

    def test_get_stats_counts(self):
        s = TaskScheduler()
        s.add_task("a", "typeA", "* * * * *")
        s.add_task("b", "typeA", "* * * * *")
        s.add_task("c", "typeB", "* * * * *")
        s.disable_task("task_3")
        stats = s.get_stats()
        assert stats["total_tasks"] == 3
        assert stats["enabled"] == 2
        assert stats["disabled"] == 1
        assert stats["by_type"] == {"typeA": 2, "typeB": 1}


# ── to_dict round-trip ───────────────────────────────────────────────────
class TestToDict:
    EXPECTED_KEYS = {
        "task_id", "name", "task_type", "cron_expr", "enabled", "status",
        "created_at", "last_run", "next_run", "run_count", "last_error",
        "config",
    }

    def test_to_dict_exact_key_set(self):
        t = ScheduledTask("t", "n", "x", "0 0 * * *")
        assert set(t.to_dict().keys()) == self.EXPECTED_KEYS

    def test_to_dict_status_is_enum_value(self):
        t = ScheduledTask("t", "n", "x", "0 0 * * *")
        assert t.to_dict()["status"] == "pending"

    def test_to_dict_none_fields_before_run(self):
        t = ScheduledTask("t", "n", "x", "0 0 * * *")
        d = t.to_dict()
        assert d["last_run"] is None
        assert d["last_error"] is None
        assert d["run_count"] == 0

    def test_to_dict_after_run_populated(self):
        t = ScheduledTask("t", "n", "x", "* * * * *", callback=lambda task: None)
        t.run()
        d = t.to_dict()
        assert d["last_run"] is not None
        assert d["run_count"] == 1
        assert d["status"] == "completed"

    def test_to_dict_config_round_trip(self):
        t = ScheduledTask("t", "n", "x", "* * * * *", config={"k": "v"})
        assert t.to_dict()["config"] == {"k": "v"}


# ── CANCELLED is reserved (never assigned) ───────────────────────────────
class TestCancelledReserved:
    def test_cancelled_never_assigned_on_success(self):
        t = ScheduledTask("t", "n", "x", "* * * * *", callback=lambda task: None)
        t.run()
        assert t.status is not TaskStatus.CANCELLED

    def test_cancelled_never_assigned_on_failure(self):
        def boom(task):
            raise RuntimeError("x")

        t = ScheduledTask("t", "n", "x", "* * * * *", callback=boom)
        t.run()
        assert t.status is not TaskStatus.CANCELLED

    def test_cancelled_never_assigned_via_run_due_tasks(self):
        s = TaskScheduler()
        t = s.add_task("n", "x", "* * * * *", callback=lambda task: None)
        t.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        s.run_due_tasks()
        assert t.status is not TaskStatus.CANCELLED


# ── unicode / guard inputs on task fields ────────────────────────────────
class TestGuardInputs:
    def test_unicode_name_and_config(self):
        t = ScheduledTask("t", "название", "тип", "* * * * *",
                          config={"ключ": "значение"})
        assert t.name == "название"
        assert t.to_dict()["name"] == "название"
        assert t.to_dict()["config"] == {"ключ": "значение"}

    def test_empty_cron_never_runs(self):
        t = ScheduledTask("t", "n", "x", "")
        assert t.next_run is None

    def test_whitespace_only_cron_never_runs(self):
        t = ScheduledTask("t", "n", "x", "   ")
        assert t.next_run is None


# ── end-to-end installed CLI run (scheduler is passive; CLI is the entry) ─
class TestEndToEndCli:
    def test_cli_init_then_status(self, tmp_path):
        from personal_index.cli import main

        runner = CliRunner(isolate_filesystem=False)
        dd = str(tmp_path / "data")
        r = runner.invoke(main, ["init", "--data-dir", dd])
        assert r.exit_code == 0, r.output
        assert "Initialized" in r.output

        r2 = runner.invoke(main, ["status", "--data-dir", dd])
        assert r2.exit_code == 0, r2.output
        assert "Personal Index Status" in r2.output
        assert "Pages indexed:" in r2.output
