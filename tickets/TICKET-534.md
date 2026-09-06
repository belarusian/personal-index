# TICKET-534: SnapshotManager.create_snapshot docstring omits max_snapshots eviction contract

Status: OPEN
Module: personal_index/content_diff/snapshot.py
Method: SnapshotManager.create_snapshot

## Symptom
The `create_snapshot` docstring describes only the happy path (create a
Snapshot, append it, return it). It does NOT state the exact eviction
contract: when the per-item snapshot count exceeds `self.max_snapshots`,
the OLDEST snapshots are dropped and only the last `max_snapshots` are
retained. A reader of the docstring cannot tell that calling
`create_snapshot` can silently remove previously-created snapshots of the
same item.

## Evidence
personal_index/content_diff/snapshot.py, create_snapshot body:

    self.snapshots.setdefault(item_id, []).append(snapshot)

    # Enforce max snapshots
    if len(self.snapshots[item_id]) > self.max_snapshots:
        self.snapshots[item_id] = self.snapshots[item_id][-self.max_snapshots:]

Current docstring (lines ~46-55) says only:
    "Create a new snapshot of a content item."
with Args (item, id_field, label) and Returns (The created Snapshot).
No mention of max_snapshots, eviction, or oldest-first dropping.

Existing behavioral test already pins the eviction (tests/test_snapshot.py
TestSnapshotManager.test_max_snapshots_enforced): with max_snapshots=3 and
5 creates, len==3 and snaps[0].data["v"]==2 (oldest two evicted). The
behavior is correct; only the docstring contract is missing.

## Minimal additive fix
Reword the create_snapshot docstring to state the exact contract:
  - appends a new Snapshot for the item and returns it;
  - when the item's snapshot count exceeds max_snapshots, the oldest
    snapshots are evicted so only the last max_snapshots are retained;
  - snapshot_id is built from item_id, a UTC timestamp, and a monotonically
    increasing counter.
Add a pinning test class TestCreateSnapshotDocstring534 (mirror
TestClearDocstring533) asserting the docstring states the eviction contract
(key phrases: "max_snapshots", "evict"/"drop"/"retain", "oldest").

## Issue
Issue: #943
