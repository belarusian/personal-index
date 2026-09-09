"""Adversarial deep tests for personal_index.progress (validator cycle 156).

Covers the ProgressTracker state machine, ProgressStore persistence,
guard inputs (None/empty/whitespace/unicode/duplicate/out-of-range),
round-trips, idempotence, property checks, and one end-to-end CLI run.

Also anchors the CLASS SWEEP for the negative-slice "top N / recent N"
defect class (QA-1 extract_top_n, QA-2 tfidf + index.search, QA-3
Feed.get_recent_entries): ProgressStore.list_completed(limit) is a 4th
site of the same class and is pinned here as xfail-strict (QA-4).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from personal_index.progress import (
    ProgressState,
    ProgressStore,
    ProgressTracker,
)


# ---------------------------------------------------------------------------
# ProgressTracker state machine
# ---------------------------------------------------------------------------

def test_start_sets_running_and_timestamp():
    t = ProgressTracker(operation_name="op")
    assert t.state == ProgressState.PENDING.value
    t.start()
    assert t.state == ProgressState.RUNNING.value
    assert t.started_at is not None


def test_pause_only_from_running():
    t = ProgressTracker(operation_name="op")
    t.pause()  # not running -> no-op
    assert t.state == ProgressState.PENDING.value
    t.start()
    t.pause()
    assert t.state == ProgressState.PAUSED.value


def test_resume_only_from_paused():
    t = ProgressTracker(operation_name="op")
    t.resume()  # not paused -> no-op
    assert t.state == ProgressState.PENDING.value
    t.start()
    t.pause()
    t.resume()
    assert t.state == ProgressState.RUNNING.value


def test_complete_sets_completed_and_caps_current():
    t = ProgressTracker(operation_name="op", total_steps=4)
    t.start()
    t.advance("a")
    t.complete()
    assert t.state == ProgressState.COMPLETED.value
    assert t.current_step == 4
    assert t.completed_at is not None


def test_fail_records_message():
    t = ProgressTracker(operation_name="op")
    t.start()
    t.fail("boom")
    assert t.state == ProgressState.FAILED.value
    assert t.message == "boom"
    assert t.completed_at is not None


def test_cancel():
    t = ProgressTracker(operation_name="op")
    t.start()
    t.cancel()
    assert t.state == ProgressState.CANCELLED.value
    assert t.completed_at is not None


# ---------------------------------------------------------------------------
# progress_percent / elapsed / estimated_remaining guards
# ---------------------------------------------------------------------------

def test_progress_percent_zero_total_is_zero():
    t = ProgressTracker(operation_name="op", total_steps=0)
    assert t.progress_percent == 0.0


def test_progress_percent_clamped_to_100():
    t = ProgressTracker(operation_name="op", total_steps=2, current_step=5)
    assert t.progress_percent == 100.0


def test_progress_percent_midpoint():
    t = ProgressTracker(operation_name="op", total_steps=4, current_step=2)
    assert t.progress_percent == 50.0


def test_elapsed_seconds_no_start_is_zero():
    t = ProgressTracker(operation_name="op")
    assert t.elapsed_seconds == 0.0


def test_elapsed_seconds_bad_timestamp_is_zero():
    t = ProgressTracker(operation_name="op")
    t.started_at = "not-a-timestamp"
    assert t.elapsed_seconds == 0.0


def test_estimated_remaining_zero_step_is_zero():
    t = ProgressTracker(operation_name="op", total_steps=4, current_step=0)
    assert t.estimated_remaining == 0.0


# ---------------------------------------------------------------------------
# advance: idempotence / cap / state gating
# ---------------------------------------------------------------------------

def test_advance_noop_when_not_running():
    t = ProgressTracker(operation_name="op", total_steps=3)
    t.advance("a")  # pending -> no-op
    assert t.current_step == 0
    assert t.steps == []


def test_advance_caps_at_total():
    t = ProgressTracker(operation_name="op", total_steps=2)
    t.start()
    for _ in range(5):
        t.advance("x")
    # current_step is capped at total_steps even when over-advanced.
    assert t.current_step == 2
    assert t.progress_percent == 100.0


def test_advance_records_step_details():
    t = ProgressTracker(operation_name="op", total_steps=3)
    t.start()
    t.advance("do it", {"k": "v"})
    assert t.steps[0]["description"] == "do it"
    assert t.steps[0]["details"] == {"k": "v"}
    assert t.steps[0]["completed"] is True


# ---------------------------------------------------------------------------
# to_dict / from_dict round-trip + extra-key tolerance
# ---------------------------------------------------------------------------

def test_to_dict_from_dict_round_trip():
    t = ProgressTracker(operation_name="op", total_steps=3,
                        metadata={"m": 1})
    t.start()
    t.advance("a")
    d = t.to_dict()
    t2 = ProgressTracker.from_dict(d)
    assert t2.operation_name == "op"
    assert t2.total_steps == 3
    assert t2.current_step == 1
    assert t2.metadata == {"m": 1}
    assert len(t2.steps) == 1


def test_from_dict_ignores_extra_keys():
    t = ProgressTracker(operation_name="op", total_steps=1)
    d = t.to_dict()
    d["bogus_key"] = "should be dropped"
    d["progress_percent"] = 99.0  # not a constructor field
    t2 = ProgressTracker.from_dict(d)
    assert t2.operation_name == "op"
    assert not hasattr(t2, "bogus_key")


def test_from_dict_empty_dict_generates_id():
    t = ProgressTracker.from_dict({})
    assert t.operation_id  # auto-generated
    assert t.state == "pending"


# ---------------------------------------------------------------------------
# format_bar
# ---------------------------------------------------------------------------

def test_format_bar_full_and_empty():
    full = ProgressTracker(operation_name="op", total_steps=1, current_step=1)
    bar = full.format_bar(10)
    assert bar.startswith("[") and bar.endswith("100.0%")
    empty = ProgressTracker(operation_name="op", total_steps=1, current_step=0)
    assert empty.format_bar(10).endswith("0.0%")


# ---------------------------------------------------------------------------
# ProgressStore: create / get / remove / list
# ---------------------------------------------------------------------------

def test_store_create_get_remove():
    s = ProgressStore()
    t = s.create("op", total_steps=1)
    assert s.get(t.operation_id) is t
    assert s.remove(t.operation_id) is True
    assert s.remove(t.operation_id) is False
    assert s.get(t.operation_id) is None


def test_store_list_active_filters_by_state():
    s = ProgressStore()
    running = s.create("run", total_steps=1)
    running.start()
    paused = s.create("pause", total_steps=1)
    paused.start()
    paused.pause()
    done = s.create("done", total_steps=1)
    done.start()
    done.complete()
    active_ids = {t.operation_id for t in s.list_active()}
    assert running.operation_id in active_ids
    assert paused.operation_id in active_ids
    assert done.operation_id not in active_ids


def test_store_list_completed_zero_limit_empty():
    s = ProgressStore()
    for i in range(3):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    assert s.list_completed(0) == []


def test_store_list_completed_positive_limit():
    s = ProgressStore()
    for i in range(5):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    assert len(s.list_completed(2)) == 2


def test_list_completed_negative_limit_returns_empty():
    s = ProgressStore()
    for i in range(3):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    # Out-of-range (negative) limit must yield an empty list, matching limit=0.
    assert s.list_completed(-1) == []


# ---------------------------------------------------------------------------
# ProgressStore: cleanup
# ---------------------------------------------------------------------------

def test_cleanup_removes_oldest_completed():
    s = ProgressStore()
    for i in range(5):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    removed = s.cleanup(max_keep=2)
    assert removed == 3
    assert len(s._trackers) == 2


def test_cleanup_noop_when_under_limit():
    s = ProgressStore()
    for i in range(2):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    assert s.cleanup(max_keep=50) == 0
    assert len(s._trackers) == 2


# ---------------------------------------------------------------------------
# ProgressStore: save_all / load_all round-trip + corrupt input
# ---------------------------------------------------------------------------

def test_save_load_round_trip(tmp_path):
    p = tmp_path / "prog.json"
    s = ProgressStore(storage_path=str(p))
    for i in range(3):
        t = s.create(f"op{i}", total_steps=1)
        t.start()
        t.complete()
    s.save_all()
    s2 = ProgressStore(storage_path=str(p))
    assert s2.load_all() == 3
    assert all(t.state == ProgressState.COMPLETED.value
               for t in s2._trackers.values())


def test_load_all_corrupt_json_returns_zero(tmp_path):
    p = tmp_path / "prog.json"
    p.write_text("{ this is not valid json")
    s = ProgressStore(storage_path=str(p))
    assert s.load_all() == 0


def test_load_all_non_dict_returns_zero(tmp_path):
    p = tmp_path / "prog.json"
    p.write_text("[1, 2, 3]")
    s = ProgressStore(storage_path=str(p))
    assert s.load_all() == 0


def test_save_all_no_path_is_noop():
    s = ProgressStore()  # no storage path
    s.create("op", total_steps=1)
    s.save_all()  # must not raise
    assert s.load_all() == 0


# ---------------------------------------------------------------------------
# unicode / whitespace / duplicate guard inputs
# ---------------------------------------------------------------------------

def test_unicode_operation_name_round_trip():
    t = ProgressTracker(operation_name="операция 🚀", total_steps=1)
    d = t.to_dict()
    t2 = ProgressTracker.from_dict(d)
    assert t2.operation_name == "операция 🚀"


def test_whitespace_operation_name_preserved():
    t = ProgressTracker(operation_name="   ", total_steps=1)
    assert t.operation_name == "   "
    assert t.operation_id  # still auto-generated


def test_duplicate_create_gets_distinct_ids():
    s = ProgressStore()
    a = s.create("same", total_steps=1)
    b = s.create("same", total_steps=1)
    assert a.operation_id != b.operation_id
    assert len(s._trackers) == 2


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
