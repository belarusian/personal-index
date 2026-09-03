"""Tests for progress tracking."""

from __future__ import annotations

import time

from personal_index.progress import (
    ProgressState,
    ProgressStore,
    ProgressTracker,
)


class TestProgressTracker:
    """Tests for ProgressTracker dataclass."""

    def test_create_tracker(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        assert t.operation_id
        assert t.state == "pending"
        assert t.total_steps == 10

    def test_progress_percent_empty(self):
        t = ProgressTracker(operation_name="test")
        assert t.progress_percent == 0.0

    def test_progress_percent_half(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.current_step = 5
        assert t.progress_percent == 50.0

    def test_progress_percent_complete(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.current_step = 10
        assert t.progress_percent == 100.0

    def test_progress_percent_over_100(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.current_step = 15
        assert t.progress_percent == 100.0

    def test_start(self):
        t = ProgressTracker(operation_name="test")
        t.start()
        assert t.state == ProgressState.RUNNING.value
        assert t.started_at

    def test_pause(self):
        t = ProgressTracker(operation_name="test")
        t.start()
        t.pause()
        assert t.state == ProgressState.PAUSED.value

    def test_resume(self):
        t = ProgressTracker(operation_name="test")
        t.start()
        t.pause()
        t.resume()
        assert t.state == ProgressState.RUNNING.value

    def test_complete(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.start()
        t.complete()
        assert t.state == ProgressState.COMPLETED.value
        assert t.current_step == 10
        assert t.completed_at

    def test_fail(self):
        t = ProgressTracker(operation_name="test")
        t.start()
        t.fail("Something went wrong")
        assert t.state == ProgressState.FAILED.value
        assert t.message == "Something went wrong"

    def test_cancel(self):
        t = ProgressTracker(operation_name="test")
        t.start()
        t.cancel()
        assert t.state == ProgressState.CANCELLED.value

    def test_advance(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.start()
        t.advance("Processing page 1")
        assert t.current_step == 1
        assert len(t.steps) == 1
        assert t.steps[0]["description"] == "Processing page 1"

    def test_advance_when_not_running(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.advance("Should not advance")
        assert t.current_step == 0

    def test_advance_caps_at_total(self):
        t = ProgressTracker(operation_name="test", total_steps=2)
        t.start()
        t.advance()
        t.advance()
        t.advance()
        assert t.current_step == 2

    def test_set_total(self):
        t = ProgressTracker(operation_name="test")
        t.set_total(100)
        assert t.total_steps == 100

    def test_set_message(self):
        t = ProgressTracker(operation_name="test")
        t.set_message("Processing...")
        assert t.message == "Processing..."

    def test_to_dict(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.start()
        t.advance()
        d = t.to_dict()
        assert d["operation_name"] == "test"
        assert d["progress_percent"] == 10.0
        assert "elapsed_seconds" in d

    def test_format_bar(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.current_step = 5
        bar = t.format_bar(width=20)
        assert "50.0%" in bar
        assert "█" in bar

    def test_elapsed_seconds(self):
        t = ProgressTracker(operation_name="test")
        t.start()
        time.sleep(0.1)
        assert t.elapsed_seconds >= 0.1

    def test_elapsed_seconds_corrupt_started_at(self):
        # A non-ISO started_at (e.g. from corrupt persisted storage) must not raise.
        t = ProgressTracker.from_dict({
            "operation_name": "x",
            "state": "running",
            "total_steps": 10,
            "current_step": 2,
            "started_at": "not-a-timestamp",
        })
        assert t.elapsed_seconds == 0.0

    def test_elapsed_seconds_non_string_started_at(self):
        # A non-string started_at (e.g. a number from JSON) must not raise.
        t = ProgressTracker.from_dict({
            "operation_name": "x",
            "state": "running",
            "total_steps": 10,
            "current_step": 2,
            "started_at": 12345,
        })
        assert t.elapsed_seconds == 0.0

    def test_to_dict_with_corrupt_started_at(self):
        # to_dict calls elapsed_seconds; a corrupt started_at must not crash it.
        t = ProgressTracker.from_dict({
            "operation_name": "x",
            "state": "running",
            "total_steps": 10,
            "current_step": 2,
            "started_at": "garbage",
        })
        d = t.to_dict()
        assert d["elapsed_seconds"] == 0.0

    def test_estimated_remaining(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.start()
        time.sleep(0.1)
        t.current_step = 5
        assert t.estimated_remaining > 0


class TestProgressStore:
    """Tests for ProgressStore class."""

    def test_create_tracker(self):
        store = ProgressStore()
        t = store.create("test crawl", total_steps=10)
        assert store.get(t.operation_id) is t

    def test_get_nonexistent(self):
        store = ProgressStore()
        assert store.get("nonexistent") is None

    def test_list_active(self):
        store = ProgressStore()
        t1 = store.create("crawl1", total_steps=10)
        t1.start()
        t2 = store.create("crawl2", total_steps=5)
        t2.start()
        t2.complete()
        active = store.list_active()
        assert len(active) == 1
        assert active[0].operation_name == "crawl1"

    def test_list_completed(self):
        store = ProgressStore()
        t1 = store.create("crawl1", total_steps=10)
        t1.start()
        t1.complete()
        completed = store.list_completed()
        assert len(completed) == 1

    def test_remove(self):
        store = ProgressStore()
        t = store.create("test", total_steps=10)
        assert store.remove(t.operation_id) is True
        assert store.get(t.operation_id) is None

    def test_remove_nonexistent(self):
        store = ProgressStore()
        assert store.remove("nonexistent") is False

    def test_cleanup(self):
        store = ProgressStore()
        for i in range(10):
            t = store.create(f"crawl{i}", total_steps=1)
            t.start()
            t.complete()
        removed = store.cleanup(max_keep=3)
        assert removed == 7

    def test_save_and_load(self, tmp_path):
        store = ProgressStore(storage_path=str(tmp_path / "progress.json"))
        t = store.create("test", total_steps=10)
        t.start()
        t.advance()
        store.save_all()

        new_store = ProgressStore(storage_path=str(tmp_path / "progress.json"))
        count = new_store.load_all()
        assert count == 1
        loaded = new_store.get(t.operation_id)
        assert loaded is not None
        assert loaded.operation_name == "test"

    def test_load_nonexistent(self, tmp_path):
        store = ProgressStore(storage_path=str(tmp_path / "progress.json"))
        count = store.load_all()
        assert count == 0

    def test_load_all_null_json(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text("null")
        store = ProgressStore(storage_path=str(path))
        count = store.load_all()
        assert count == 0

    def test_load_all_list_json(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text("[1, 2, 3]")
        store = ProgressStore(storage_path=str(path))
        count = store.load_all()
        assert count == 0

    def test_load_all_number_json(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text("42")
        store = ProgressStore(storage_path=str(path))
        count = store.load_all()
        assert count == 0

    def test_load_all_corrupt_json(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text("{")
        store = ProgressStore(storage_path=str(path))
        count = store.load_all()
        assert count == 0

    def test_load_all_truncated_json(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text('{"op_1": {"operation_id": "op_1", "state": "run')
        store = ProgressStore(storage_path=str(path))
        count = store.load_all()
        assert count == 0

    def test_load_all_corrupt_started_at(self, tmp_path):
        # A persisted file with a non-ISO started_at loads fine and reading
        # elapsed_seconds on the loaded tracker must not raise.
        path = tmp_path / "progress.json"
        path.write_text(
            '{"op1": {"operation_name": "x", "state": "running",'
            ' "total_steps": 10, "current_step": 2, "started_at": "garbage"}}'
        )
        store = ProgressStore(storage_path=str(path))
        count = store.load_all()
        assert count == 1
        loaded = store.get("op1")
        assert loaded is not None
        assert loaded.elapsed_seconds == 0.0
        # to_dict (which calls elapsed_seconds) must not crash either.
        assert loaded.to_dict()["elapsed_seconds"] == 0.0

    def test_auto_generate_operation_id(self):
        t = ProgressTracker()
        assert t.operation_id.startswith("op_")
        assert len(t.operation_id) > 10

    def test_from_dict(self):
        d = {
            "operation_id": "op_123",
            "operation_name": "import",
            "state": "running",
            "total_steps": 20,
            "current_step": 10,
            "steps": [],
            "started_at": "2025-01-01T00:00:00+00:00",
            "completed_at": None,
            "message": "halfway",
            "metadata": {"src": "csv"},
        }
        t = ProgressTracker.from_dict(d)
        assert t.operation_id == "op_123"
        assert t.operation_name == "import"
        assert t.state == "running"
        assert t.total_steps == 20
        assert t.current_step == 10
        assert t.message == "halfway"
        assert t.metadata == {"src": "csv"}

    def test_from_dict_ignores_extra_keys(self):
        d = {
            "operation_id": "op_456",
            "operation_name": "test",
            "state": "pending",
            "total_steps": 5,
            "current_step": 0,
            "steps": [],
            "started_at": None,
            "completed_at": None,
            "message": "",
            "metadata": {},
            "extra_field": "should_be_ignored",
            "another_extra": 42,
        }
        t = ProgressTracker.from_dict(d)
        assert t.operation_id == "op_456"
        assert not hasattr(t, "extra_field")

    def test_pause_when_not_running(self):
        t = ProgressTracker(operation_name="test")
        assert t.state == "pending"
        t.pause()
        assert t.state == "pending"

    def test_resume_when_not_paused(self):
        t = ProgressTracker(operation_name="test")
        t.resume()
        assert t.state == "pending"

    def test_format_bar_zero_percent(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        bar = t.format_bar(width=10)
        assert "0.0%" in bar

    def test_format_bar_full(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.current_step = 10
        bar = t.format_bar(width=10)
        assert "100.0%" in bar

    def test_elapsed_no_start(self):
        t = ProgressTracker(operation_name="test")
        assert t.elapsed_seconds == 0.0

    def test_estimated_remaining_zero_step(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.start()
        assert t.estimated_remaining == 0.0

    def test_advance_with_details(self):
        t = ProgressTracker(operation_name="test", total_steps=5)
        t.start()
        t.advance("step one", {"pages": 12})
        assert t.steps[0]["details"]["pages"] == 12

    def test_complete_sets_current_to_total(self):
        t = ProgressTracker(operation_name="test", total_steps=10)
        t.start()
        t.advance()
        t.advance()
        t.complete()
        assert t.current_step == 10
        assert t.progress_percent == 100.0

    def test_fail_sets_completed_at(self):
        t = ProgressTracker(operation_name="test")
        t.start()
        t.fail("error")
        assert t.completed_at is not None

    def test_cancel_sets_completed_at(self):
        t = ProgressTracker(operation_name="test")
        t.start()
        t.cancel()
        assert t.completed_at is not None

    def test_progress_step_to_dict(self):
        from personal_index.progress import ProgressStep
        step = ProgressStep(step_id="s1", description="crawl", completed=True, details={"url": "x"})
        d = step.to_dict()
        assert d["step_id"] == "s1"
        assert d["description"] == "crawl"
        assert d["completed"] is True
        assert d["details"]["url"] == "x"

    def test_store_save_no_storage_path(self):
        store = ProgressStore()
        store.create("test", total_steps=5)
        store.save_all()

    def test_store_load_no_storage_path(self):
        store = ProgressStore()
        assert store.load_all() == 0

    def test_store_cleanup_nothing_to_remove(self):
        store = ProgressStore()
        removed = store.cleanup(max_keep=50)
        assert removed == 0

    def test_store_list_completed_limit(self):
        store = ProgressStore()
        for i in range(10):
            t = store.create(f"op{i}", total_steps=1)
            t.start()
            t.complete()
        completed = store.list_completed(limit=3)
        assert len(completed) == 3

    def test_store_list_active_includes_paused(self):
        store = ProgressStore()
        t1 = store.create("run", total_steps=10)
        t1.start()
        t2 = store.create("pause", total_steps=10)
        t2.start()
        t2.pause()
        active = store.list_active()
        assert len(active) == 2

    def test_store_save_load_multiple(self, tmp_path):
        store = ProgressStore(storage_path=str(tmp_path / "prog.json"))
        t1 = store.create("a", total_steps=5)
        t1.start()
        t2 = store.create("b", total_steps=3)
        t2.start()
        store.save_all()
        new_store = ProgressStore(storage_path=str(tmp_path / "prog.json"))
        count = new_store.load_all()
        assert count == 2
        assert new_store.get(t1.operation_id) is not None
        assert new_store.get(t2.operation_id) is not None

    def test_tracker_metadata_default(self):
        t = ProgressTracker(operation_name="test")
        assert t.metadata == {}

    def test_store_create_with_metadata(self):
        store = ProgressStore()
        t = store.create("test", metadata={"key": "val"})
        assert t.metadata == {"key": "val"}

    def test_to_dict_roundtrip(self):
        t = ProgressTracker(operation_name="roundtrip", total_steps=20)
        t.start()
        t.advance("first")
        t.advance("second")
        t.set_message("going well")
        d = t.to_dict()
        t2 = ProgressTracker.from_dict(d)
        assert t2.operation_name == "roundtrip"
        assert t2.total_steps == 20
        assert t2.current_step == 2
        assert t2.message == "going well"
        assert len(t2.steps) == 2
