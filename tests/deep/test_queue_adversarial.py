"""Adversarial deep tests for personal_index/queue.py (TaskQueue / Task).

PROBE target for validator cycle 161 (never-probed subsystem).

docs/queue.md is the exact contract. The module's primary hole - `_evict_lowest`
drops the *highest*-priority task on overflow while logging "dropping lowest
priority task" - is ALREADY ticketed as ARCH-38 (Status: OPEN). It is pinned
here with xfail-strict so the suite stays green while the defect exists and the
test flips to a hard pass once the implementer fixes it. No new QA ticket is
filed for it (ARCH-38 owns the finding; re-filing would be a duplicate).

Everything else in this file is clean regression armor for the documented
behavior: priority ordering, FIFO tie-break, guard inputs (None/empty/
whitespace/unicode/duplicate/out-of-range), round-trips, idempotence, property
checks, and one end-to-end run through the installed CLI.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from personal_index.queue import (
    Task,
    TaskPriority,
    TaskQueue,
    TaskStatus,
)


# ---------------------------------------------------------------------------
# Priority ordering + FIFO tie-break (the core contract)
# ---------------------------------------------------------------------------
class TestPriorityOrdering:
    def test_lower_priority_value_dequeued_first(self):
        q = TaskQueue()
        q.enqueue("low", priority=TaskPriority.LOW)
        q.enqueue("crit", priority=TaskPriority.CRITICAL)
        q.enqueue("high", priority=TaskPriority.HIGH)
        q.enqueue("bg", priority=TaskPriority.BACKGROUND)
        q.enqueue("norm", priority=TaskPriority.NORMAL)
        order = [q.dequeue().task_id for _ in range(5)]
        assert order == ["crit", "high", "norm", "low", "bg"]

    def test_fifo_tie_break_within_same_priority(self):
        q = TaskQueue()
        for x in "abcde":
            q.enqueue(x, priority=TaskPriority.NORMAL)
        order = [q.dequeue().task_id for _ in range(5)]
        assert order == ["a", "b", "c", "d", "e"]

    def test_priority_beats_sequence(self):
        # A later-enqueued CRITICAL must jump ahead of an earlier NORMAL.
        q = TaskQueue()
        q.enqueue("early-norm", priority=TaskPriority.NORMAL)
        q.enqueue("late-crit", priority=TaskPriority.CRITICAL)
        assert q.dequeue().task_id == "late-crit"
        assert q.dequeue().task_id == "early-norm"

    def test_dequeue_empty_returns_none(self):
        assert TaskQueue().dequeue() is None

    def test_dequeue_marks_task_running(self):
        q = TaskQueue()
        q.enqueue("a")
        t = q.dequeue()
        assert t.status == TaskStatus.RUNNING
        assert t.started_at is not None


# ---------------------------------------------------------------------------
# Guard inputs: None / empty / whitespace / unicode / duplicate / out-of-range
# ---------------------------------------------------------------------------
class TestGuardInputs:
    def test_data_none_becomes_empty_dict(self):
        t = TaskQueue().enqueue("a", data=None)
        assert t.data == {}

    def test_data_dict_round_trips(self):
        payload = {"k": "v", "n": 3}
        t = TaskQueue().enqueue("a", data=payload)
        assert t.data == payload

    def test_empty_task_id_round_trips(self):
        q = TaskQueue()
        q.enqueue("")
        assert q.get_task("") is not None

    def test_whitespace_task_id_round_trips(self):
        q = TaskQueue()
        q.enqueue("   ")
        assert q.get_task("   ") is not None

    def test_unicode_task_id_and_name_round_trip(self):
        q = TaskQueue()
        q.enqueue("id-ünïcode", name="нàмè-日本語")
        t = q.get_task("id-ünïcode")
        assert t is not None
        assert t.name == "нàмè-日本語"

    def test_get_task_missing_returns_none(self):
        assert TaskQueue().get_task("nope") is None

    def test_duplicate_task_id_overwrites_lookup(self):
        # Documented secondary hole: a second enqueue with the same id replaces
        # the dict entry; the first task object may still sit in the heap.
        q = TaskQueue()
        t1 = q.enqueue("a", name="first")
        t2 = q.enqueue("a", name="second")
        assert q.get_task("a") is t2
        assert t1 is not t2
        # The stale first task is still dequeue-able (documented behavior).
        assert any(x.task_id == "a" for x in q._heap)


# ---------------------------------------------------------------------------
# Lifecycle guards (status transitions)
# ---------------------------------------------------------------------------
class TestLifecycleGuards:
    def test_complete_pending_returns_false(self):
        q = TaskQueue()
        q.enqueue("a")
        assert q.complete_task("a") is False

    def test_fail_pending_returns_false(self):
        q = TaskQueue()
        q.enqueue("a")
        assert q.fail_task("a", "boom") is False

    def test_cancel_missing_returns_false(self):
        assert TaskQueue().cancel_task("nope") is False

    def test_cancel_running_returns_false(self):
        q = TaskQueue()
        q.enqueue("a")
        q.dequeue()  # -> RUNNING
        assert q.cancel_task("a") is False

    def test_complete_completed_returns_false(self):
        q = TaskQueue()
        q.enqueue("a")
        q.dequeue()
        assert q.complete_task("a") is True
        assert q.complete_task("a") is False  # already COMPLETED

    def test_fail_completed_returns_false(self):
        q = TaskQueue()
        q.enqueue("a")
        q.dequeue()
        assert q.complete_task("a") is True
        assert q.fail_task("a", "x") is False

    def test_complete_running_appends_to_completed(self):
        q = TaskQueue()
        q.enqueue("a")
        q.dequeue()
        assert q.completed_count == 0
        assert q.complete_task("a", result="ok") is True
        assert q.completed_count == 1
        assert q.get_task("a").result == "ok"

    def test_fail_running_records_error(self):
        q = TaskQueue()
        q.enqueue("a")
        q.dequeue()
        assert q.fail_task("a", "kaboom") is True
        assert q.get_task("a").error == "kaboom"
        assert q.get_task("a").status == TaskStatus.FAILED

    def test_cancel_pending_leaves_in_heap_then_discarded(self):
        # Documented: a cancelled task stays in the heap until a later dequeue
        # pops and discards it.
        q = TaskQueue()
        q.enqueue("a")
        q.enqueue("b")
        assert q.cancel_task("a") is True
        assert q.size == 2          # still in heap
        assert q.pending_count == 1  # only b is pending
        assert q.dequeue().task_id == "b"  # a is skipped/discarded
        assert q.dequeue() is None


# ---------------------------------------------------------------------------
# Introspection: size / pending_count / completed_count / get_stats
# ---------------------------------------------------------------------------
class TestIntrospection:
    def test_size_and_pending_on_fresh_queue(self):
        q = TaskQueue()
        assert q.size == 0
        assert q.pending_count == 0
        assert q.completed_count == 0

    def test_size_counts_heap_including_cancelled(self):
        q = TaskQueue()
        q.enqueue("a")
        q.enqueue("b")
        q.cancel_task("a")
        assert q.size == 2
        assert q.pending_count == 1

    def test_get_stats_mixes_populations(self):
        # Documented secondary hole: queue_size counts the heap, total_tasks
        # counts the _tasks dict (which also holds dequeued RUNNING tasks).
        q = TaskQueue()
        q.enqueue("a")
        q.dequeue()  # a is now RUNNING, out of the heap but in _tasks
        s = q.get_stats()
        assert s["queue_size"] == 0
        assert s["total_tasks"] == 1
        assert s["status_breakdown"] == {"running": 1}

    def test_get_stats_empty(self):
        s = TaskQueue().get_stats()
        assert s == {
            "queue_size": 0,
            "total_tasks": 0,
            "completed": 0,
            "status_breakdown": {},
        }


# ---------------------------------------------------------------------------
# clear_completed: trim + idempotence
# ---------------------------------------------------------------------------
class TestClearCompleted:
    def _fill(self, n):
        q = TaskQueue()
        for i in range(n):
            q.enqueue(f"t{i}")
            q.dequeue()
            q.complete_task(f"t{i}")
        return q

    def test_trims_to_keep(self):
        q = self._fill(5)
        assert q.completed_count == 5
        q.clear_completed(keep=2)
        assert q.completed_count == 2

    def test_no_trim_when_at_or_below_keep(self):
        q = self._fill(2)
        q.clear_completed(keep=100)
        assert q.completed_count == 2

    def test_idempotent(self):
        q = self._fill(5)
        q.clear_completed(keep=2)
        q.clear_completed(keep=2)
        assert q.completed_count == 2

    def test_keeps_most_recent(self):
        q = self._fill(5)
        q.clear_completed(keep=2)
        kept = [t.task_id for t in q._completed]
        assert kept == ["t3", "t4"]


# ---------------------------------------------------------------------------
# max_size out-of-range (documented: unvalidated)
# ---------------------------------------------------------------------------
class TestMaxSize:
    def test_max_size_zero_never_holds_more_than_one(self):
        # Documented secondary hole: max_size <= 0 makes the overflow check
        # true on the very first enqueue, so each enqueue evicts the
        # predecessor and the queue never holds more than one task.
        q = TaskQueue(max_size=0)
        q.enqueue("a")
        q.enqueue("b")
        assert q.size == 1
        assert q.get_task("a") is None  # evicted
        assert q.get_task("b") is not None

    def test_negative_max_size_does_not_raise(self):
        q = TaskQueue(max_size=-5)
        q.enqueue("a")
        q.enqueue("b")
        assert q.size == 1


# ---------------------------------------------------------------------------
# Task.duration property
# ---------------------------------------------------------------------------
class TestDuration:
    def test_none_before_start(self):
        assert Task(priority=2, sequence=0, task_id="x").duration is None

    def test_none_after_start_only(self):
        t = Task(priority=2, sequence=0, task_id="x")
        t.start()
        assert t.duration is None

    def test_positive_after_complete(self):
        t = Task(priority=2, sequence=0, task_id="x")
        t.start()
        t.complete("ok")
        assert t.duration is not None
        assert t.duration >= 0


# ---------------------------------------------------------------------------
# ARCH-38 (OPEN): _evict_lowest drops the HIGHEST-priority task on overflow.
# Pinned xfail-strict: documents the defect without breaking the suite; flips
# to a hard pass once the implementer makes overflow evict the least-important
# task (the heap maximum), per the defensible contract in docs/queue.md.
# ---------------------------------------------------------------------------
class TestEvictLowestDefect:
    @pytest.mark.xfail(
        strict=True,
        reason="ARCH-38: on overflow _evict_lowest pops the heap MINIMUM "
               "(the highest-priority task) and cancels it, while logging "
               "'dropping lowest priority task'. The CRITICAL task must be "
               "kept and the BACKGROUND task evicted.",
    )
    def test_overflow_keeps_critical_evicts_background(self):
        q = TaskQueue(max_size=2)
        q.enqueue("crit", priority=TaskPriority.CRITICAL)
        q.enqueue("bg", priority=TaskPriority.BACKGROUND)
        # Queue is full; enqueueing a third task must evict the least-important
        # (BACKGROUND), keeping CRITICAL.
        q.enqueue("norm", priority=TaskPriority.NORMAL)
        assert q.get_task("crit") is not None, "CRITICAL task was evicted"
        assert q.get_task("bg") is None, "BACKGROUND task should have been evicted"


# ---------------------------------------------------------------------------
# End-to-end through the installed CLI (package-level smoke; the queue module
# is not directly exposed on the CLI, so this exercises the installed entry
# point to confirm the package imports and runs cleanly).
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_cli_search_empty_index(self, tmp_path):
        data_dir = str(tmp_path / "data")
        env = dict(os.environ)
        srch = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "search", "python"],
            capture_output=True, text=True, env=env,
        )
        assert srch.returncode == 0, srch.stderr
        assert "No indexed content found" in srch.stdout
