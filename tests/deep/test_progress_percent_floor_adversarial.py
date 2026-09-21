"""Adversarial deep tests for personal_index.progress (validator cycle 346).

Focus: the ``progress_percent`` contract "Get progress as percentage (0-100)."
The code clamps the TOP (``min(100.0, ...)``) but has NO floor
(``max(0.0, ...)``), so a negative ``current_step`` or ``total_steps`` leaks a
NEGATIVE percentage — the one-sided-guard (cap-without-floor) defect class
(QA-15/QA-16/QA-31). Pinned here as xfail-strict (QA-71).

Also armor-pins the GUARDED behaviors the module already delivers correctly:
format_bar width guards, list_completed limit guards (incl. negative + huge),
cleanup negative max_keep, from_dict empty/None, and the QA-63
elapsed_seconds naive/aware->UTC normalization. One end-to-end CLI run.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from personal_index.progress import (
    ProgressState,
    ProgressStore,
    ProgressTracker,
)


# ---------------------------------------------------------------------------
# QA-71: progress_percent floor (cap-without-floor) — xfail-strict pins
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason="QA-71: progress_percent docstring promises 0-100 but has no "
           "lower clamp (max(0.0, ...)); negative current_step leaks -50.0",
)
def test_progress_percent_negative_current_step_is_floored():
    t = ProgressTracker(operation_name="x", total_steps=10, current_step=-5)
    p = t.progress_percent
    # Contract: "Get progress as percentage (0-100)."
    assert 0.0 <= p <= 100.0, f"progress_percent out of 0-100: {p}"


@pytest.mark.xfail(
    strict=True,
    reason="QA-71: progress_percent has no lower clamp; negative total_steps "
           "leaks a negative percentage",
)
def test_progress_percent_negative_total_steps_is_floored():
    t = ProgressTracker(operation_name="x", total_steps=-10, current_step=5)
    p = t.progress_percent
    assert 0.0 <= p <= 100.0, f"progress_percent out of 0-100: {p}"


@pytest.mark.xfail(
    strict=True,
    reason="QA-71: the public to_dict() serialization path exposes the same "
           "unfloored progress_percent",
)
def test_to_dict_progress_percent_floored():
    t = ProgressTracker(operation_name="x", total_steps=10, current_step=-5)
    d = t.to_dict()
    assert 0.0 <= d["progress_percent"] <= 100.0, (
        f"to_dict progress_percent out of 0-100: {d['progress_percent']}"
    )


# ---------------------------------------------------------------------------
# Armor: progress_percent behaviors the module ALREADY delivers correctly
# ---------------------------------------------------------------------------

def test_progress_percent_zero_total_is_zero():
    t = ProgressTracker(operation_name="x", total_steps=0, current_step=5)
    assert t.progress_percent == 0.0


def test_progress_percent_clamped_to_100_when_over():
    # current > total is GUARDED by the min(100.0, ...) upper clamp.
    t = ProgressTracker(operation_name="x", total_steps=10, current_step=15)
    assert t.progress_percent == 100.0


def test_progress_percent_midpoint():
    t = ProgressTracker(operation_name="x", total_steps=10, current_step=3)
    assert t.progress_percent == 30.0


# ---------------------------------------------------------------------------
# Armor: format_bar width guards
# ---------------------------------------------------------------------------

def test_format_bar_width_zero_is_empty_bar():
    t = ProgressTracker(operation_name="x", total_steps=10, current_step=5)
    bar = t.format_bar(0)
    assert bar.startswith("[") and bar.endswith("] 50.0%")
    # width 0 -> no fill/empty glyphs between the brackets
    inner = bar[1:bar.rindex("]")]
    assert inner == ""


def test_format_bar_negative_width_does_not_raise():
    t = ProgressTracker(operation_name="x", total_steps=10, current_step=5)
    # Negative width must not raise (int() of a negative fill is clamped to 0
    # by the string-multiplication semantics); it degrades to an empty bar.
    bar = t.format_bar(-5)
    assert bar.startswith("[") and bar.endswith("] 50.0%")


def test_format_bar_width_matches_percent():
    t = ProgressTracker(operation_name="x", total_steps=10, current_step=5)
    bar = t.format_bar(40)
    # 50% of 40 = 20 filled glyphs
    inner = bar[1:bar.rindex("]")]
    assert inner.count("\u2588") == 20  # █
    assert inner.count("\u2591") == 20  # ░


# ---------------------------------------------------------------------------
# Armor: list_completed limit guards (negative + huge)
# ---------------------------------------------------------------------------

def test_list_completed_negative_limit_is_empty():
    s = ProgressStore()
    for i in range(3):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    assert s.list_completed(-1) == []
    assert s.list_completed(0) == []


def test_list_completed_huge_limit_returns_all():
    s = ProgressStore()
    for i in range(3):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    assert len(s.list_completed(10**9)) == 3


def test_list_completed_positive_limit_caps():
    s = ProgressStore()
    for i in range(5):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    assert len(s.list_completed(2)) == 2


# ---------------------------------------------------------------------------
# Armor: cleanup negative max_keep
# ---------------------------------------------------------------------------

def test_cleanup_negative_max_keep_removes_all_but_one():
    # max_keep=-1 -> keep -1 (i.e. none), so all completed are removed except
    # the slice semantics: completed[-1:] is kept. Document the actual shape.
    s = ProgressStore()
    for i in range(5):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    removed = s.cleanup(max_keep=-1)
    # len(completed)=5 > max_keep=-1 -> remove completed[-1:] = 1 tracker
    assert removed == 1
    assert len(s._trackers) == 4


def test_cleanup_noop_when_under_limit():
    s = ProgressStore()
    for i in range(2):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    assert s.cleanup(max_keep=50) == 0
    assert len(s._trackers) == 2


# ---------------------------------------------------------------------------
# Armor: from_dict empty / None values
# ---------------------------------------------------------------------------

def test_from_dict_empty_dict_generates_id():
    t = ProgressTracker.from_dict({})
    assert t.operation_id  # auto-generated
    assert t.state == ProgressState.PENDING.value


def test_from_dict_none_steps_preserved():
    t = ProgressTracker.from_dict(
        {"operation_id": "x", "total_steps": None, "current_step": None}
    )
    # from_dict passes None through (no coercion); the tracker tolerates it.
    assert t.total_steps is None
    assert t.current_step is None


def test_from_dict_ignores_extra_keys():
    t = ProgressTracker.from_dict(
        {"operation_id": "x", "bogus": 1, "total_steps": 3}
    )
    assert t.operation_id == "x"
    assert t.total_steps == 3
    assert not hasattr(t, "bogus")


# ---------------------------------------------------------------------------
# Armor: QA-63 elapsed_seconds naive/aware -> UTC normalization
# ---------------------------------------------------------------------------

def test_elapsed_seconds_naive_start_is_nonnegative():
    # QA-63: naive started_at normalized to UTC before (now - start), so the
    # property returns a non-negative float instead of raising TypeError.
    t = ProgressTracker(operation_name="x", total_steps=4, current_step=2)
    t.started_at = "2020-01-01T00:00:00"  # naive
    assert t.elapsed_seconds >= 0.0


def test_elapsed_seconds_aware_start_is_nonnegative():
    t = ProgressTracker(operation_name="x", total_steps=4, current_step=2)
    t.started_at = "2020-01-01T05:00:00+05:00"  # aware +05:00
    assert t.elapsed_seconds >= 0.0


def test_elapsed_seconds_garbage_is_zero():
    t = ProgressTracker(operation_name="x", total_steps=4, current_step=2)
    t.started_at = "garbage"
    assert t.elapsed_seconds == 0.0


def test_elapsed_seconds_no_start_is_zero():
    t = ProgressTracker(operation_name="x", total_steps=4)
    assert t.elapsed_seconds == 0.0


# ---------------------------------------------------------------------------
# Armor: estimated_remaining zero-step guard
# ---------------------------------------------------------------------------

def test_estimated_remaining_zero_step_is_zero():
    t = ProgressTracker(operation_name="x", total_steps=10, current_step=0)
    t.started_at = "2020-01-01T00:00:00+00:00"
    assert t.estimated_remaining == 0.0


# ---------------------------------------------------------------------------
# Armor: state machine idempotence (complete/fail/cancel are terminal no-ops
# on re-entry for the timestamp, but state is set deterministically)
# ---------------------------------------------------------------------------

def test_complete_is_idempotent_state():
    t = ProgressTracker(operation_name="x", total_steps=4)
    t.start()
    t.complete()
    first_state = t.state
    t.complete()
    assert t.state == first_state == ProgressState.COMPLETED.value
    # completed_at is re-stamped on each complete() call (not idempotent on
    # the timestamp) — pin the STATE idempotence, which is the contract.
    assert t.completed_at is not None


def test_pause_resume_round_trip():
    t = ProgressTracker(operation_name="x", total_steps=4)
    t.start()
    t.pause()
    assert t.state == ProgressState.PAUSED.value
    t.resume()
    assert t.state == ProgressState.RUNNING.value


# ---------------------------------------------------------------------------
# end-to-end CLI run (installed CLI)
# ---------------------------------------------------------------------------

def test_cli_end_to_end_init_import_search():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "init",
             "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        f = data_dir / "page.html"
        f.write_text(
            "<html><body><h1>python programming</h1>"
            "<p>python is great</p></body></html>"
        )
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "import", str(f),
             "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "search", "python",
             "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "python" in (r.stdout + r.stderr).lower()
