"""Adversarial deep tests for personal_index.content_diff (ContentDiff + SnapshotManager).

Covers:
- ContentDiff.compute: empty items, None values, unicode, missing id fields,
  nested dicts, same item, all added, all removed, mixed changes, summary text,
  has_changes, change_count, get_changes_by_type
- SnapshotManager: empty item, None id, unicode id, max_snapshots=0/1, eviction,
  unknown item queries, diff_snapshots missing, get_history edge cases,
  multiple items
"""

from __future__ import annotations


from personal_index.content_diff import ChangeType, ContentDiff, SnapshotManager


# ============================================================================
# ContentDiff.compute edge cases
# ============================================================================

def test_compute_empty_items():
    """Both items empty -> no changes."""
    diff = ContentDiff.compute({}, {})
    assert diff.item_id == "unknown"
    assert diff.changes == []
    assert diff.summary == "No changes"
    assert not diff.has_changes
    assert diff.change_count == 0


def test_compute_old_empty_all_added():
    """Old item empty -> all fields in new are ADDED."""
    diff = ContentDiff.compute({}, {"id": "1", "title": "New", "content": "Hello"})
    assert diff.item_id == "1"
    assert diff.change_count == 3
    added = diff.get_changes_by_type(ChangeType.ADDED)
    assert len(added) == 3
    fields = {c.field for c in added}
    assert fields == {"id", "title", "content"}
    assert "3 added" in diff.summary


def test_compute_new_empty_all_removed():
    """New item empty -> all fields in old are REMOVED."""
    diff = ContentDiff.compute({"id": "1", "title": "Old"}, {})
    assert diff.item_id == "1"
    assert diff.change_count == 2
    removed = diff.get_changes_by_type(ChangeType.REMOVED)
    assert len(removed) == 2
    assert "2 removed" in diff.summary


def test_compute_same_item_no_changes():
    """Identical items -> no changes."""
    item = {"id": "1", "title": "Same", "content": "Same"}
    diff = ContentDiff.compute(item, item)
    assert diff.changes == []
    assert diff.summary == "No changes"
    assert not diff.has_changes


def test_compute_modified_field():
    """Single field modified."""
    old = {"id": "1", "title": "Old Title"}
    new = {"id": "1", "title": "New Title"}
    diff = ContentDiff.compute(old, new)
    assert diff.change_count == 1
    modified = diff.get_changes_by_type(ChangeType.MODIFIED)
    assert len(modified) == 1
    assert modified[0].field == "title"
    assert modified[0].old_value == "Old Title"
    assert modified[0].new_value == "New Title"
    assert "1 modified" in diff.summary


def test_compute_mixed_changes():
    """Added, removed, and modified fields together."""
    old = {"id": "1", "title": "Old", "removed_field": "gone"}
    new = {"id": "1", "title": "New", "added_field": "new"}
    diff = ContentDiff.compute(old, new)
    assert diff.change_count == 3
    assert len(diff.get_changes_by_type(ChangeType.ADDED)) == 1
    assert len(diff.get_changes_by_type(ChangeType.REMOVED)) == 1
    assert len(diff.get_changes_by_type(ChangeType.MODIFIED)) == 1
    assert "1 added, 1 removed, 1 modified" in diff.summary


def test_compute_none_values():
    """None values are treated as distinct from missing fields."""
    old = {"id": "1", "title": None}
    new = {"id": "1"}
    diff = ContentDiff.compute(old, new)
    # title is present in old with value None, absent in new -> REMOVED
    removed = diff.get_changes_by_type(ChangeType.REMOVED)
    assert len(removed) == 1
    assert removed[0].field == "title"
    assert removed[0].old_value is None


def test_compute_none_to_value():
    """Field changes from None to a value -> MODIFIED."""
    old = {"id": "1", "title": None}
    new = {"id": "1", "title": "Now set"}
    diff = ContentDiff.compute(old, new)
    modified = diff.get_changes_by_type(ChangeType.MODIFIED)
    assert len(modified) == 1
    assert modified[0].field == "title"
    assert modified[0].old_value is None
    assert modified[0].new_value == "Now set"


def test_compute_unicode_values():
    """Unicode values are compared correctly."""
    old = {"id": "1", "title": "Café"}
    new = {"id": "1", "title": "Café ☕"}
    diff = ContentDiff.compute(old, new)
    assert diff.change_count == 1
    modified = diff.get_changes_by_type(ChangeType.MODIFIED)
    assert modified[0].new_value == "Café ☕"


def test_compute_unicode_field_names():
    """Unicode field names are handled."""
    old = {"id": "1", "日本語": "old"}
    new = {"id": "1", "日本語": "new"}
    diff = ContentDiff.compute(old, new)
    assert diff.change_count == 1
    assert diff.changes[0].field == "日本語"


def test_compute_missing_id_falls_back_to_old():
    """If new item has no id, fall back to old item's id."""
    old = {"id": "1", "title": "Old"}
    new = {"title": "New"}
    diff = ContentDiff.compute(old, new)
    assert diff.item_id == "1"


def test_compute_both_missing_id():
    """If neither item has id, item_id is 'unknown'."""
    diff = ContentDiff.compute({"title": "Old"}, {"title": "New"})
    assert diff.item_id == "unknown"


def test_compute_custom_id_field():
    """Custom id_field parameter."""
    old = {"item_id": "42", "title": "Old"}
    new = {"item_id": "42", "title": "New"}
    diff = ContentDiff.compute(old, new, id_field="item_id")
    assert diff.item_id == "42"


def test_compute_nested_dict_values():
    """Nested dicts are compared by equality."""
    old = {"id": "1", "meta": {"key": "old"}}
    new = {"id": "1", "meta": {"key": "new"}}
    diff = ContentDiff.compute(old, new)
    assert diff.change_count == 1
    modified = diff.get_changes_by_type(ChangeType.MODIFIED)
    assert modified[0].field == "meta"
    assert modified[0].old_value == {"key": "old"}
    assert modified[0].new_value == {"key": "new"}


def test_compute_list_values():
    """List values are compared by equality."""
    old = {"id": "1", "tags": ["a", "b"]}
    new = {"id": "1", "tags": ["a", "b", "c"]}
    diff = ContentDiff.compute(old, new)
    assert diff.change_count == 1
    modified = diff.get_changes_by_type(ChangeType.MODIFIED)
    assert modified[0].field == "tags"


def test_compute_fields_sorted():
    """Changes are returned in sorted field name order."""
    old = {"id": "1", "z_field": "old", "a_field": "old"}
    new = {"id": "1", "z_field": "new", "a_field": "new"}
    diff = ContentDiff.compute(old, new)
    assert [c.field for c in diff.changes] == ["a_field", "z_field"]


def test_get_changes_by_type_unchanged():
    """UNCHANGED type returns empty list (unchanged fields are dropped)."""
    diff = ContentDiff.compute({"id": "1", "title": "Same"}, {"id": "1", "title": "Same"})
    unchanged = diff.get_changes_by_type(ChangeType.UNCHANGED)
    assert unchanged == []


# ============================================================================
# SnapshotManager edge cases
# ============================================================================

def test_create_snapshot_basic():
    """Basic snapshot creation."""
    mgr = SnapshotManager()
    item = {"id": "1", "title": "Test"}
    snap = mgr.create_snapshot(item)
    assert snap.snapshot_id.startswith("1_")
    assert snap.data == item
    assert snap.label == ""


def test_create_snapshot_with_label():
    """Snapshot with custom label."""
    mgr = SnapshotManager()
    item = {"id": "1", "title": "Test"}
    snap = mgr.create_snapshot(item, label="v1.0")
    assert snap.label == "v1.0"


def test_create_snapshot_none_id():
    """Item with None id -> item_id is 'None' (str(None))."""
    mgr = SnapshotManager()
    item = {"id": None, "title": "Test"}
    snap = mgr.create_snapshot(item)
    assert snap.snapshot_id.startswith("None_")
    assert "None" in mgr.snapshots


def test_create_snapshot_missing_id():
    """Item with missing id -> item_id is 'unknown'."""
    mgr = SnapshotManager()
    item = {"title": "Test"}
    snap = mgr.create_snapshot(item)
    assert snap.snapshot_id.startswith("unknown_")
    assert "unknown" in mgr.snapshots


def test_create_snapshot_unicode_id():
    """Item with unicode id."""
    mgr = SnapshotManager()
    item = {"id": "café-1", "title": "Test"}
    snap = mgr.create_snapshot(item)
    assert snap.snapshot_id.startswith("café-1_")


def test_create_snapshot_empty_item():
    """Snapshot of empty item."""
    mgr = SnapshotManager()
    snap = mgr.create_snapshot({})
    assert snap.data == {}
    assert "unknown" in mgr.snapshots


def test_max_snapshots_zero():
    """max_snapshots=0 -> all snapshots evicted immediately."""
    mgr = SnapshotManager(max_snapshots=0)
    item = {"id": "1", "title": "Test"}
    mgr.create_snapshot(item)
    assert mgr.snapshots["1"] == []
    assert mgr.get_snapshots("1") == []
    assert mgr.get_latest("1") is None


def test_max_snapshots_one():
    """max_snapshots=1 -> only latest retained."""
    mgr = SnapshotManager(max_snapshots=1)
    item = {"id": "1"}
    mgr.create_snapshot({**item, "title": "v1"})
    mgr.create_snapshot({**item, "title": "v2"})
    snaps = mgr.get_snapshots("1")
    assert len(snaps) == 1
    assert snaps[0].data["title"] == "v2"
    assert mgr.get_latest("1").data["title"] == "v2"


def test_max_snapshots_eviction():
    """Eviction keeps only the last N snapshots."""
    mgr = SnapshotManager(max_snapshots=3)
    item = {"id": "1"}
    for i in range(5):
        mgr.create_snapshot({**item, "version": i})
    snaps = mgr.get_snapshots("1")
    assert len(snaps) == 3
    # Should have versions 2, 3, 4 (last 3)
    versions = [s.data["version"] for s in snaps]
    assert versions == [2, 3, 4]


def test_eviction_does_not_affect_other_items():
    """Eviction for one item doesn't touch other items' snapshots."""
    mgr = SnapshotManager(max_snapshots=2)
    for i in range(5):
        mgr.create_snapshot({"id": "1", "version": i})
    for i in range(3):
        mgr.create_snapshot({"id": "2", "version": i})
    assert len(mgr.get_snapshots("1")) == 2
    assert len(mgr.get_snapshots("2")) == 2  # Evicted to max_snapshots


def test_get_snapshots_unknown_item():
    """get_snapshots for unknown item returns empty list."""
    mgr = SnapshotManager()
    assert mgr.get_snapshots("nonexistent") == []


def test_get_latest_unknown_item():
    """get_latest for unknown item returns None."""
    mgr = SnapshotManager()
    assert mgr.get_latest("nonexistent") is None


def test_get_snapshots_sorted_by_timestamp():
    """Snapshots are returned sorted by timestamp."""
    mgr = SnapshotManager()
    item = {"id": "1"}
    mgr.create_snapshot({**item, "v": 1})
    mgr.create_snapshot({**item, "v": 2})
    mgr.create_snapshot({**item, "v": 3})
    snaps = mgr.get_snapshots("1")
    timestamps = [s.timestamp for s in snaps]
    assert timestamps == sorted(timestamps)


def test_diff_snapshots_basic():
    """Diff between two snapshots."""
    mgr = SnapshotManager()
    snap1 = mgr.create_snapshot({"id": "1", "title": "Old"})
    snap2 = mgr.create_snapshot({"id": "1", "title": "New"})
    diff = mgr.diff_snapshots("1", snap1.snapshot_id, snap2.snapshot_id)
    assert diff is not None
    assert diff.change_count == 1
    modified = diff.get_changes_by_type(ChangeType.MODIFIED)
    assert modified[0].field == "title"


def test_diff_snapshots_missing_old():
    """diff_snapshots returns None if old snapshot not found."""
    mgr = SnapshotManager()
    snap = mgr.create_snapshot({"id": "1", "title": "Test"})
    diff = mgr.diff_snapshots("1", "nonexistent", snap.snapshot_id)
    assert diff is None


def test_diff_snapshots_missing_new():
    """diff_snapshots returns None if new snapshot not found."""
    mgr = SnapshotManager()
    snap = mgr.create_snapshot({"id": "1", "title": "Test"})
    diff = mgr.diff_snapshots("1", snap.snapshot_id, "nonexistent")
    assert diff is None


def test_diff_snapshots_unknown_item():
    """diff_snapshots returns None for unknown item."""
    mgr = SnapshotManager()
    diff = mgr.diff_snapshots("unknown", "id1", "id2")
    assert diff is None


def test_get_history_no_snapshots():
    """get_history with no snapshots returns empty list."""
    mgr = SnapshotManager()
    assert mgr.get_history("1") == []


def test_get_history_one_snapshot():
    """get_history with one snapshot returns empty list (no pairs to diff)."""
    mgr = SnapshotManager()
    mgr.create_snapshot({"id": "1", "title": "v1"})
    assert mgr.get_history("1") == []


def test_get_history_multiple_snapshots():
    """get_history returns diffs between consecutive snapshots."""
    mgr = SnapshotManager()
    mgr.create_snapshot({"id": "1", "title": "v1"})
    mgr.create_snapshot({"id": "1", "title": "v2"})
    mgr.create_snapshot({"id": "1", "title": "v3"})
    history = mgr.get_history("1")
    assert len(history) == 2  # v1->v2, v2->v3
    # First diff: v1 -> v2
    assert history[0].change_count == 1
    modified = history[0].get_changes_by_type(ChangeType.MODIFIED)
    assert modified[0].old_value == "v1"
    assert modified[0].new_value == "v2"


def test_multiple_items_independent():
    """Multiple items have independent snapshot histories."""
    mgr = SnapshotManager()
    mgr.create_snapshot({"id": "1", "title": "A"})
    mgr.create_snapshot({"id": "2", "title": "B"})
    mgr.create_snapshot({"id": "1", "title": "A2"})
    assert len(mgr.get_snapshots("1")) == 2
    assert len(mgr.get_snapshots("2")) == 1
    assert mgr.get_latest("1").data["title"] == "A2"
    assert mgr.get_latest("2").data["title"] == "B"


def test_snapshot_data_is_copy():
    """Snapshot stores a copy of the data, not a reference."""
    mgr = SnapshotManager()
    item = {"id": "1", "title": "Original"}
    mgr.create_snapshot(item)
    item["title"] = "Modified after snapshot"
    snap = mgr.get_latest("1")
    assert snap.data["title"] == "Original"
