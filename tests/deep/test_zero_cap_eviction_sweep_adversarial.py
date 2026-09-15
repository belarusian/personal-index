"""CLASS SWEEP: zero-cap eviction slicing gotcha across the codebase.

Defect class (QA-25): several retention/eviction sites cap a list with
``if len(lst) > cap: lst = lst[-cap:]``. When ``cap == 0`` Python's
``lst[-0:]`` is ``lst[0:]`` == the FULL list, so a zero cap silently keeps
EVERY entry instead of none. This is the same slicing-gotcha family as the
negative-slice "top N" leaks (QA-15 content_summarizer.summarize, QA-16
content_search.SearchIndex.search), but for the eviction-cap idiom.

Whole-codebase sweep (grep ``[-self.<cap>:]`` / ``[-<cap>:]`` over
personal_index/) found FIVE public sites, all unguarded against cap==0:

  1. personal_index/versioning.py:93            VersionTracker.record_version
  2. personal_index/content_diff/snapshot.py:83 SnapshotManager.create_snapshot
  3. personal_index/performance_monitor.py:85   PerformanceMonitor.record
  4. personal_index/content_monitor/alert.py:84 AlertManager.add_alert
  5. personal_index/notifications.py:168        InMemoryHandler.handle

Each test below is xfail-strict: it documents the EXPECTED contract (a zero
cap keeps zero entries) and currently FAILS (the cap is ignored). When the
implementer adds a ``cap <= 0`` guard, all five flip to XPASS -> strict
failure forces the ticket to be re-verified and closed. Validator does NOT
fix product code.
"""

from __future__ import annotations

from personal_index.content_diff.snapshot import SnapshotManager
from personal_index.content_monitor.alert import AlertLevel, AlertManager
from personal_index.notifications import InMemoryHandler, Notification
from personal_index.performance_monitor import PerformanceMonitor
from personal_index.versioning import VersionTracker


def test_versioning_zero_cap_keeps_none():
    t = VersionTracker(max_versions=0)
    for i in range(3):
        t.record_version("http://x.com", f"c{i}")
    assert t.get_versions("http://x.com") == []


def test_snapshot_zero_cap_keeps_none():
    sm = SnapshotManager(max_snapshots=0)
    for i in range(3):
        sm.create_snapshot({"id": "x", "v": i})
    assert sm.get_snapshots("x") == []


def test_performance_zero_cap_keeps_none():
    pm = PerformanceMonitor(window_size=0)
    for i in range(3):
        pm.record("m", float(i))
    assert pm.get_recent_samples("m", count=100) == []


def test_alert_zero_cap_keeps_none():
    am = AlertManager(max_alerts=0)
    for i in range(3):
        am.add_alert(AlertLevel.INFO, f"m{i}", "s")
    assert am.alerts == []


def test_notification_zero_cap_keeps_none():
    h = InMemoryHandler(max_size=0)
    for i in range(3):
        h.handle(Notification(title=f"t{i}"))
    assert h._notifications == []


# ---------------------------------------------------------------------------
# ARMOR: the positive cap path works correctly at all five sites (this is the
# documented behavior and must keep passing; it distinguishes the zero-cap
# defect from a broken cap in general).
# ---------------------------------------------------------------------------

def test_versioning_positive_cap_enforced():
    t = VersionTracker(max_versions=2)
    for i in range(5):
        t.record_version("http://x.com", f"c{i}")
    assert len(t.get_versions("http://x.com")) == 2


def test_snapshot_positive_cap_enforced():
    sm = SnapshotManager(max_snapshots=2)
    for i in range(5):
        sm.create_snapshot({"id": "x", "v": i})
    assert len(sm.get_snapshots("x")) == 2


def test_performance_positive_cap_enforced():
    pm = PerformanceMonitor(window_size=2)
    for i in range(5):
        pm.record("m", float(i))
    assert len(pm.get_recent_samples("m", count=100)) == 2


def test_alert_positive_cap_enforced():
    am = AlertManager(max_alerts=2)
    for i in range(5):
        am.add_alert(AlertLevel.INFO, f"m{i}", "s")
    assert len(am.alerts) == 2


def test_notification_positive_cap_enforced():
    h = InMemoryHandler(max_size=2)
    for i in range(5):
        h.handle(Notification(title=f"t{i}"))
    assert len(h._notifications) == 2


# ---------------------------------------------------------------------------
# ARMOR (cycle 246, QA-25 verify): the guard is ``cap <= 0`` (not ``cap == 0``),
# so the contract must hold for NEGATIVE caps too (out-of-range adversarial
# input). A negative cap must evict to empty, exactly like a zero cap. These
# pins prove the guard is the ``<= 0`` form and not a ``== 0`` special-case
# that would leak a partial page on a negative cap (the one-sided-guard class
# from the negative-slice "top N" sweep, QA-15/QA-16/QA-31).
# ---------------------------------------------------------------------------

def test_versioning_negative_cap_keeps_none():
    t = VersionTracker(max_versions=-5)
    for i in range(3):
        t.record_version("http://x.com", f"c{i}")
    assert t.get_versions("http://x.com") == []


def test_snapshot_negative_cap_keeps_none():
    sm = SnapshotManager(max_snapshots=-5)
    for i in range(3):
        sm.create_snapshot({"id": "x", "v": i})
    assert sm.get_snapshots("x") == []


def test_performance_negative_cap_keeps_none():
    pm = PerformanceMonitor(window_size=-5)
    for i in range(3):
        pm.record("m", float(i))
    assert pm.get_recent_samples("m", count=100) == []


def test_alert_negative_cap_keeps_none():
    am = AlertManager(max_alerts=-5)
    for i in range(3):
        am.add_alert(AlertLevel.INFO, f"m{i}", "s")
    assert am.alerts == []


def test_notification_negative_cap_keeps_none():
    h = InMemoryHandler(max_size=-5)
    for i in range(3):
        h.handle(Notification(title=f"t{i}"))
    assert h._notifications == []


# ---------------------------------------------------------------------------
# ARMOR (cycle 246, QA-25 verify): the cap=1 boundary. A cap of exactly 1 must
# keep exactly the most-recent single entry (distinguishes the zero-cap guard
# from a broken cap in general, and pins the off-by-one at the smallest
# positive value).
# ---------------------------------------------------------------------------

def test_versioning_cap_one_keeps_last():
    t = VersionTracker(max_versions=1)
    for i in range(3):
        t.record_version("http://x.com", f"c{i}")
    assert len(t.get_versions("http://x.com")) == 1


def test_snapshot_cap_one_keeps_last():
    sm = SnapshotManager(max_snapshots=1)
    for i in range(3):
        sm.create_snapshot({"id": "x", "v": i})
    snaps = sm.get_snapshots("x")
    assert len(snaps) == 1


def test_performance_cap_one_keeps_last():
    pm = PerformanceMonitor(window_size=1)
    for i in range(3):
        pm.record("m", float(i))
    samples = pm.get_recent_samples("m", count=100)
    assert len(samples) == 1


def test_alert_cap_one_keeps_last():
    am = AlertManager(max_alerts=1)
    for i in range(3):
        am.add_alert(AlertLevel.INFO, f"m{i}", "s")
    assert len(am.alerts) == 1


def test_notification_cap_one_keeps_last():
    h = InMemoryHandler(max_size=1)
    for i in range(3):
        h.handle(Notification(title=f"t{i}"))
    assert len(h._notifications) == 1
