"""Tests for snapshot management."""

from datetime import datetime, timezone

from personal_index.content_diff.snapshot import Snapshot, SnapshotManager


class TestSnapshot:
    def test_creation(self):
        s = Snapshot(snapshot_id="s1", timestamp=datetime.now(timezone.utc), data={"id": "1"})
        assert s.snapshot_id == "s1"
        assert s.label == ""

    def test_label(self):
        s = Snapshot(snapshot_id="s1", timestamp=datetime.now(timezone.utc), data={}, label="v1")
        assert s.label == "v1"


class TestSnapshotManager:
    def test_create_snapshot(self):
        mgr = SnapshotManager()
        snap = mgr.create_snapshot({"id": "1", "title": "A"})
        assert snap.snapshot_id.startswith("1_")
        assert snap.data == {"id": "1", "title": "A"}

    def test_create_snapshot_label(self):
        mgr = SnapshotManager()
        snap = mgr.create_snapshot({"id": "1"}, label="initial")
        assert snap.label == "initial"

    def test_get_snapshots(self):
        mgr = SnapshotManager()
        mgr.create_snapshot({"id": "1", "v": 1})
        mgr.create_snapshot({"id": "1", "v": 2})
        snaps = mgr.get_snapshots("1")
        assert len(snaps) == 2

    def test_get_snapshots_empty(self):
        mgr = SnapshotManager()
        assert mgr.get_snapshots("nonexistent") == []

    def test_get_latest(self):
        mgr = SnapshotManager()
        mgr.create_snapshot({"id": "1", "v": 1})
        latest = mgr.get_latest("1")
        assert latest is not None
        assert latest.data["v"] == 1

    def test_get_latest_none(self):
        mgr = SnapshotManager()
        assert mgr.get_latest("nonexistent") is None

    def test_max_snapshots_enforced(self):
        mgr = SnapshotManager(max_snapshots=3)
        for i in range(5):
            mgr.create_snapshot({"id": "1", "v": i})
        snaps = mgr.get_snapshots("1")
        assert len(snaps) == 3
        assert snaps[0].data["v"] == 2

    def test_diff_snapshots(self):
        mgr = SnapshotManager()
        s1 = mgr.create_snapshot({"id": "1", "title": "A"})
        s2 = mgr.create_snapshot({"id": "1", "title": "B"})
        diff = mgr.diff_snapshots("1", s1.snapshot_id, s2.snapshot_id)
        assert diff is not None
        assert diff.has_changes is True

    def test_diff_snapshots_not_found(self):
        mgr = SnapshotManager()
        result = mgr.diff_snapshots("1", "nonexistent", "also_not_found")
        assert result is None

    def test_get_history(self):
        mgr = SnapshotManager()
        mgr.create_snapshot({"id": "1", "v": 1})
        mgr.create_snapshot({"id": "1", "v": 2})
        mgr.create_snapshot({"id": "1", "v": 3})
        history = mgr.get_history("1")
        assert len(history) == 2

    def test_get_history_empty(self):
        mgr = SnapshotManager()
        mgr.create_snapshot({"id": "1"})
        history = mgr.get_history("1")
        assert history == []

    def test_get_history_no_snapshots(self):
        mgr = SnapshotManager()
        history = mgr.get_history("nonexistent")
        assert history == []

    def test_custom_id_field(self):
        mgr = SnapshotManager()
        snap = mgr.create_snapshot({"uid": "x1", "title": "A"}, id_field="uid")
        assert snap.snapshot_id.startswith("x1_")

    def test_counter_increments(self):
        mgr = SnapshotManager()
        s1 = mgr.create_snapshot({"id": "1"})
        s2 = mgr.create_snapshot({"id": "1"})
        assert s1.snapshot_id != s2.snapshot_id


class TestCreateSnapshotDocstring534:
    """Pin the SnapshotManager.create_snapshot eviction contract (TICKET-534)."""

    def test_docstring_states_exact_contract(self):
        doc = SnapshotManager.create_snapshot.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "max_snapshots" in doc
        assert "evicted" in doc
        assert "oldest" in doc
        assert "retain" in doc
