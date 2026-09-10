"""Cycle 197 — negative-slice "top N" class sweep, pass 3.

ARCH-17 (issue #1049) is the class home: any public function that truncates a
list with ``list[:N]`` (or ``list[-N:]``) on a caller-supplied count MUST guard
``N <= 0 -> []``. Cycle 196 filed QA-27 (issue #1244) for the five
``[-N:]`` sites in url_history / performance_monitor / content_notifications /
analytics. This pass re-runs the whole-codebase sweep
(``grep -rnE '\\[-[a-z_]+\\]|\\[:-?[a-z_]+\\]|\\[:[a-z_]+\\]' personal_index/``)
and traces every hit to its public entry point.

Two NEW unguarded public sites were found that are NOT in QA-27's five and NOT
in any prior QA ticket:

1. ``personal_index/migrations/runner.py`` — ``MigrationRunner.rollback(steps)``
   does ``list(reversed(applied))[:steps]`` with no ``steps < 0`` guard.
   ``rollback(steps=-1)`` rolls back ALL-BUT-LAST (2 of 3) instead of 0.
2. ``personal_index/backup.py`` — ``BackupManager.cleanup_old_backups(keep)``
   does ``backups[:-keep]`` with no ``keep < 0`` guard.
   ``cleanup_old_backups(keep=-1)`` DELETES 1 backup instead of 0.

Both are pinned xfail-strict below and filed as QA-28. When the implementer
adds the ``N < 0 -> []`` guard, these XPASS and xfail-strict turns them red,
which is the signal to re-verify and close QA-28.

The remaining sweep hits are either (a) already guarded (``if N <= 0: return []``
or ``max(0, N)``), (b) private helpers reached only with a fixed default (no
caller-supplied count), or (c) string truncation (out of scope for the list
top-N class). See the cycle-197 sweep table in the gate log.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from personal_index.backup import BackupManager
from personal_index.migrations.base import BaseMigration, MigrationRegistry, MigrationStore
from personal_index.migrations.runner import MigrationRunner


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_migrations(n: int) -> list[type[BaseMigration]]:
    """Build ``n`` trivial BaseMigration subclasses with versions 1..n."""
    classes: list[type[BaseMigration]] = []
    for v in range(1, n + 1):
        cls = type(
            f"Mig{v}",
            (BaseMigration,),
            {
                "version": v,
                "name": f"mig{v}",
                "upgrade": lambda self: [],
                "downgrade": lambda self: [],
            },
        )
        classes.append(cls)
    return classes


def _applied_runner(n: int) -> tuple[MigrationRunner, MigrationStore]:
    """Return a runner with ``n`` migrations applied (versions 1..n)."""
    reg = MigrationRegistry()
    for cls in _make_migrations(n):
        reg.register(cls)
    store = MigrationStore()
    runner = MigrationRunner(registry=reg, store=store)
    runner.run_pending()
    return runner, store


def _make_backups(bm: BackupManager, n: int, src: Path) -> None:
    """Create ``n`` uncompressed backups of ``src``."""
    for _ in range(n):
        bm.create_backup(str(src), compress=False)


# ---------------------------------------------------------------------------
# QA-28 defect pins (xfail-strict) — migrations.rollback(steps=-1)
# ---------------------------------------------------------------------------

class TestMigrationRollbackNegativeSteps:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-28: negative-slice top-N leak, MigrationRunner.rollback(steps=-1) "
               "rolls back all-but-last instead of 0",
    )
    def test_rollback_negative_steps_returns_empty(self):
        runner, store = _applied_runner(3)
        # steps=-1 is out-of-range; contract says roll back 0 (== [])
        result = runner.rollback(steps=-1)
        assert result == []

    @pytest.mark.xfail(
        strict=True,
        reason="QA-28: negative-slice top-N leak, MigrationRunner.rollback(steps=-1) "
               "rolls back all-but-last instead of 0",
    )
    def test_rollback_negative_steps_keeps_all_applied(self):
        runner, store = _applied_runner(3)
        runner.rollback(steps=-1)
        # all 3 must remain applied (nothing rolled back)
        assert store.get_applied_versions() == [1, 2, 3]


# ---------------------------------------------------------------------------
# QA-28 defect pins (xfail-strict) — backup.cleanup_old_backups(keep=-1)
# ---------------------------------------------------------------------------

class TestBackupCleanupNegativeKeep:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-28: negative-slice top-N leak, BackupManager.cleanup_old_backups(keep=-1) "
               "deletes 1 backup instead of 0",
    )
    def test_cleanup_negative_keep_deletes_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        src = tmp / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        bm = BackupManager(backup_dir=str(tmp / "backups"))
        _make_backups(bm, 3, src)
        deleted = bm.cleanup_old_backups(keep=-1)
        assert deleted == []

    @pytest.mark.xfail(
        strict=True,
        reason="QA-28: negative-slice top-N leak, BackupManager.cleanup_old_backups(keep=-1) "
               "deletes 1 backup instead of 0",
    )
    def test_cleanup_negative_keep_keeps_all(self):
        tmp = Path(tempfile.mkdtemp())
        src = tmp / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        bm = BackupManager(backup_dir=str(tmp / "backups"))
        _make_backups(bm, 5, src)
        bm.cleanup_old_backups(keep=-1)
        # all 5 must remain (nothing deleted)
        assert len(bm.list_backups()) == 5


# ---------------------------------------------------------------------------
# clean armor — migrations.rollback (positive / zero / idempotence)
# ---------------------------------------------------------------------------

class TestMigrationRollbackArmor:
    def test_rollback_zero_steps_returns_empty(self):
        runner, store = _applied_runner(3)
        assert runner.rollback(steps=0) == []
        assert store.get_applied_versions() == [1, 2, 3]

    def test_rollback_one_step_rolls_back_latest(self):
        runner, store = _applied_runner(3)
        result = runner.rollback(steps=1)
        assert len(result) == 1
        assert store.get_applied_versions() == [1, 2]

    def test_rollback_more_than_applied_rolls_back_all(self):
        runner, store = _applied_runner(3)
        result = runner.rollback(steps=10)
        assert len(result) == 3
        assert store.get_applied_versions() == []

    def test_rollback_idempotent_when_none_applied(self):
        reg = MigrationRegistry()
        for cls in _make_migrations(2):
            reg.register(cls)
        store = MigrationStore()
        runner = MigrationRunner(registry=reg, store=store)
        # nothing applied -> rollback is a no-op
        assert runner.rollback(steps=1) == []
        assert store.get_applied_versions() == []


# ---------------------------------------------------------------------------
# clean armor — backup.cleanup_old_backups (positive / zero / idempotence)
# ---------------------------------------------------------------------------

class TestBackupCleanupArmor:
    def test_cleanup_keep_more_than_count_deletes_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        src = tmp / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        bm = BackupManager(backup_dir=str(tmp / "backups"))
        _make_backups(bm, 3, src)
        deleted = bm.cleanup_old_backups(keep=10)
        assert deleted == []
        assert len(bm.list_backups()) == 3

    def test_cleanup_keep_exact_count_deletes_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        src = tmp / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        bm = BackupManager(backup_dir=str(tmp / "backups"))
        _make_backups(bm, 3, src)
        deleted = bm.cleanup_old_backups(keep=3)
        assert deleted == []
        assert len(bm.list_backups()) == 3

    def test_cleanup_idempotent_when_no_backups(self):
        tmp = Path(tempfile.mkdtemp())
        bm = BackupManager(backup_dir=str(tmp / "backups"))
        # no backups created -> cleanup is a no-op
        assert bm.cleanup_old_backups(keep=5) == []
        assert bm.list_backups() == []
