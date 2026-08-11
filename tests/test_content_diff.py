"""Tests for content diff module."""

import pytest

from personal_index.content_diff.changes import Change, ChangeType, ContentDiff
from personal_index.content_diff.snapshot import Snapshot, SnapshotManager


class TestContentDiff:
    def test_no_changes(self) -> None:
        diff = ContentDiff.compute({"id": "1", "title": "A"}, {"id": "1", "title": "A"})
        assert diff.has_changes is False
        assert diff.summary == "No changes"

    def test_modified_field(self) -> None:
        diff = ContentDiff.compute(
            {"id": "1", "title": "Old"},
            {"id": "1", "title": "New"},
        )
        assert diff.has_changes is True
        assert diff.change_count == 1
        change = diff.changes[0]
        assert change.change_type == ChangeType.MODIFIED
        assert change.old_value == "Old"
        assert change.new_value == "New"

    def test_added_field(self) -> None:
        diff = ContentDiff.compute(
            {"id": "1"},
            {"id": "1", "tags": ["python"]},
        )
        assert diff.change_count == 1
        assert diff.changes[0].change_type == ChangeType.ADDED

    def test_removed_field(self) -> None:
        diff = ContentDiff.compute(
            {"id": "1", "tags": ["python"]},
            {"id": "1"},
        )
        assert diff.change_count == 1
        assert diff.changes[0].change_type == ChangeType.REMOVED

    def test_get_changes_by_type(self) -> None:
        diff = ContentDiff.compute(
            {"id": "1", "title": "Old", "tags": ["a"]},
            {"id": "1", "title": "New", "score": 0.5},
        )
        modified = diff.get_changes_by_type(ChangeType.MODIFIED)
        assert len(modified) == 1
        added = diff.get_changes_by_type(ChangeType.ADDED)
        assert len(added) == 1
        removed = diff.get_changes_by_type(ChangeType.REMOVED)
        assert len(removed) == 1

    def test_summary(self) -> None:
        diff = ContentDiff.compute(
            {"id": "1", "a": 1, "b": 2},
            {"id": "1", "a": 10, "c": 3},
        )
        assert "1 added" in diff.summary
        assert "1 removed" in diff.summary
        assert "1 modified" in diff.summary


class TestSnapshotManager:
    def test_create_snapshot(self) -> None:
        manager = SnapshotManager()
        snapshot = manager.create_snapshot({"id": "1", "title": "Test"})
        assert snapshot.snapshot_id.startswith("1_")
        assert snapshot.data["title"] == "Test"

    def test_get_snapshots(self) -> None:
        manager = SnapshotManager()
        manager.create_snapshot({"id": "1", "title": "V1"})
        manager.create_snapshot({"id": "1", "title": "V2"})
        snaps = manager.get_snapshots("1")
        assert len(snaps) == 2

    def test_get_latest(self) -> None:
        manager = SnapshotManager()
        manager.create_snapshot({"id": "1", "title": "V1"})
        latest = manager.get_latest("1")
        assert latest is not None
        assert latest.data["title"] == "V1"

    def test_max_snapshots(self) -> None:
        manager = SnapshotManager(max_snapshots=2)
        for i in range(5):
            manager.create_snapshot({"id": "1", "version": i})
        snaps = manager.get_snapshots("1")
        assert len(snaps) == 2

    def test_diff_snapshots(self) -> None:
        manager = SnapshotManager()
        s1 = manager.create_snapshot({"id": "1", "title": "V1"})
        s2 = manager.create_snapshot({"id": "1", "title": "V2"})
        diff = manager.diff_snapshots("1", s1.snapshot_id, s2.snapshot_id)
        assert diff is not None
        assert diff.has_changes is True

    def test_get_history(self) -> None:
        manager = SnapshotManager()
        manager.create_snapshot({"id": "1", "title": "V1"})
        manager.create_snapshot({"id": "1", "title": "V2"})
        manager.create_snapshot({"id": "1", "title": "V3"})
        history = manager.get_history("1")
        assert len(history) == 2

    def test_get_latest_not_found(self) -> None:
        manager = SnapshotManager()
        assert manager.get_latest("nonexistent") is None
