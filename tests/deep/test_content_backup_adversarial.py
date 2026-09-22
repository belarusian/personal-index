"""Adversarial deep tests for the personal_index.content_backup package.

Covers BackupStore / BackupManager / RestoreManager edge cases the
package's own tests do not: None/empty inputs, missing backup_id (None
contract), tz normalization (naive vs aware), _evict_oldest boundary,
get_latest on an empty store, export/import round-trip + corrupt-file
handling, cleanup_old_backups boundary, create_backup vs
create_incremental_backup idempotency, and merge_restore conflict
semantics.

All pins are regression armor (they must PASS). The single xfail-strict
pin documents a real contract violation (QA-75) and must be flipped to a
hard pin once the implementer fixes cleanup_old_backups.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from personal_index.content_backup.backup_manager import BackupManager
from personal_index.content_backup.backup_store import (
    BackupEntry,
    BackupStore,
    _normalize_tz,
)
from personal_index.content_backup.restore import RestoreManager

UTC = timezone.utc


def _entry(
    bid: str,
    ts: datetime,
    data: list[dict] | None = None,
    meta: dict | None = None,
) -> BackupEntry:
    return BackupEntry(
        backup_id=bid,
        timestamp=ts,
        item_count=len(data or []),
        data=data or [],
        metadata=meta or {},
    )


class TestNormalizeTz:
    """_normalize_tz: naive -> UTC-aware, aware -> unchanged."""

    def test_naive_becomes_utc_aware(self):
        naive = datetime(2020, 1, 1, 12, 30, 45)
        out = _normalize_tz(naive)
        assert out.tzinfo is not None
        assert out == datetime(2020, 1, 1, 12, 30, 45, tzinfo=UTC)

    def test_aware_utc_unchanged(self):
        aware = datetime(2020, 1, 1, 12, 30, 45, tzinfo=UTC)
        out = _normalize_tz(aware)
        assert out == aware
        assert out.tzinfo is UTC

    def test_aware_non_utc_offset_preserved(self):
        # A non-UTC aware datetime must NOT be rewritten to UTC; it is
        # returned as-is so its offset is preserved for comparison.
        from datetime import timezone as _tz

        plus2 = _tz(timedelta(hours=2))
        aware = datetime(2020, 1, 1, 12, 0, 0, tzinfo=plus2)
        out = _normalize_tz(aware)
        assert out.tzinfo is plus2
        assert out == aware


class TestAddBackup:
    """add_backup: empty/None inputs, copy semantics, id handling."""

    def test_empty_items(self):
        store = BackupStore()
        e = store.add_backup([])
        assert e.item_count == 0
        assert e.data == []

    def test_data_is_a_copy(self):
        store = BackupStore()
        items = [{"id": "a", "title": "t"}]
        e = store.add_backup(items)
        items[0]["title"] = "MUTATED"
        assert e.data[0]["title"] == "t"  # stored copy unaffected

    def test_metadata_none_becomes_empty_dict(self):
        store = BackupStore()
        e = store.add_backup([{"id": "a"}], metadata=None)
        assert e.metadata == {}

    def test_explicit_backup_id_honored(self):
        store = BackupStore()
        e = store.add_backup([{"id": "a"}], backup_id="my_id")
        assert e.backup_id == "my_id"
        assert store.get_backup("my_id") is e

    def test_auto_backup_id_when_none(self):
        store = BackupStore()
        e = store.add_backup([{"id": "a"}])
        assert e.backup_id.startswith("backup_")
        assert store.get_backup(e.backup_id) is e


class TestGetBackup:
    """get_backup: missing id -> None (not KeyError)."""

    def test_missing_id_returns_none(self):
        store = BackupStore()
        assert store.get_backup("nope") is None

    def test_found_returns_entry(self):
        store = BackupStore()
        e = store.add_backup([{"id": "a"}], backup_id="b1")
        assert store.get_backup("b1") is e


class TestListAndLatest:
    """list_backups ordering + get_latest on empty/populated store."""

    def test_list_sorted_newest_first(self):
        store = BackupStore()
        store.backups["old"] = _entry("old", datetime(2020, 1, 1, tzinfo=UTC))
        store.backups["new"] = _entry("new", datetime(2022, 1, 1, tzinfo=UTC))
        store.backups["mid"] = _entry("mid", datetime(2021, 1, 1, tzinfo=UTC))
        assert [b.backup_id for b in store.list_backups()] == ["new", "mid", "old"]

    def test_list_mixed_naive_aware_no_typeerror(self):
        # The _normalize_tz guard: a naive and an aware timestamp must not
        # raise at the sort.
        store = BackupStore()
        store.backups["naive"] = _entry("naive", datetime(2020, 1, 1))
        store.backups["aware"] = _entry("aware", datetime(2021, 1, 1, tzinfo=UTC))
        assert [b.backup_id for b in store.list_backups()] == ["aware", "naive"]

    def test_get_latest_empty_store(self):
        assert BackupStore().get_latest() is None

    def test_get_latest_returns_newest(self):
        store = BackupStore()
        store.backups["old"] = _entry("old", datetime(2020, 1, 1, tzinfo=UTC))
        store.backups["new"] = _entry("new", datetime(2022, 1, 1, tzinfo=UTC))
        assert store.get_latest().backup_id == "new"


class TestEvictOldest:
    """_evict_oldest: removes the min-timestamp entry; naive/aware safe."""

    def test_evicts_oldest(self):
        store = BackupStore(max_backups=2)
        store.backups["a"] = _entry("a", datetime(2020, 1, 1, tzinfo=UTC))
        store.backups["b"] = _entry("b", datetime(2021, 1, 1, tzinfo=UTC))
        store.backups["c"] = _entry("c", datetime(2022, 1, 1, tzinfo=UTC))
        store._evict_oldest()
        assert "a" not in store.backups
        assert set(store.backups) == {"b", "c"}

    def test_evict_mixed_naive_aware_no_typeerror(self):
        store = BackupStore()
        store.backups["naive"] = _entry("naive", datetime(2020, 1, 1))
        store.backups["aware"] = _entry("aware", datetime(2021, 1, 1, tzinfo=UTC))
        store._evict_oldest()  # must not raise
        assert "naive" not in store.backups  # naive->utc 2020 < aware 2021
        assert "aware" in store.backups

    def test_add_backup_enforces_max(self):
        store = BackupStore(max_backups=2)
        store.add_backup([{"id": "1"}], backup_id="a")
        store.add_backup([{"id": "2"}], backup_id="b")
        store.add_backup([{"id": "3"}], backup_id="c")
        assert len(store.backups) == 2


class TestDeleteBackup:
    """delete_backup: True if deleted, False if not found."""

    def test_delete_existing(self):
        store = BackupStore()
        store.add_backup([{"id": "a"}], backup_id="b1")
        assert store.delete_backup("b1") is True
        assert store.get_backup("b1") is None

    def test_delete_missing(self):
        assert BackupStore().delete_backup("nope") is False


class TestExportImport:
    """export_to_file / import_from_file round-trip + corrupt handling."""

    def test_round_trip(self, tmp_path: Path):
        store = BackupStore()
        e = store.add_backup(
            [{"id": "a", "title": "t"}, {"id": "b"}],
            backup_id="rt",
            metadata={"label": "x"},
        )
        fp = tmp_path / "out" / "b.json"
        store.export_to_file("rt", fp)
        assert fp.exists()

        store2 = BackupStore()
        e2 = store2.import_from_file(fp)
        assert e2.backup_id == "rt"
        assert e2.item_count == 2
        assert e2.data == e.data
        assert e2.metadata == {"label": "x"}
        assert e2.timestamp == e.timestamp

    def test_export_missing_id_raises_valueerror(self, tmp_path: Path):
        store = BackupStore()
        with pytest.raises(ValueError):
            store.export_to_file("nope", tmp_path / "b.json")

    def test_import_corrupt_json_raises_valueerror(self, tmp_path: Path):
        fp = tmp_path / "bad.json"
        fp.write_text("{not valid json")
        with pytest.raises(ValueError):
            BackupStore().import_from_file(fp)

    def test_import_non_dict_json_raises_valueerror(self, tmp_path: Path):
        fp = tmp_path / "list.json"
        fp.write_text(json.dumps([1, 2, 3]))
        with pytest.raises(ValueError):
            BackupStore().import_from_file(fp)

    def test_import_missing_required_key_raises_valueerror(self, tmp_path: Path):
        fp = tmp_path / "missing.json"
        fp.write_text(json.dumps({"backup_id": "x", "item_count": 0, "items": []}))
        with pytest.raises(ValueError):
            BackupStore().import_from_file(fp)

    def test_import_invalid_timestamp_raises_valueerror(self, tmp_path: Path):
        fp = tmp_path / "badts.json"
        fp.write_text(
            json.dumps(
                {
                    "backup_id": "x",
                    "timestamp": "not-a-date",
                    "item_count": 0,
                    "items": [],
                }
            )
        )
        with pytest.raises(ValueError):
            BackupStore().import_from_file(fp)


class TestBackupManager:
    """BackupManager: create/incremental/summary/cleanup contracts."""

    def test_create_backup_label_none_becomes_empty(self):
        mgr = BackupManager()
        e = mgr.create_backup([{"id": "a"}])
        assert e.metadata["label"] == ""
        assert e.metadata["created_by"] == "BackupManager"

    def test_create_backup_label_set(self):
        mgr = BackupManager()
        e = mgr.create_backup([{"id": "a"}], label="nightly")
        assert e.metadata["label"] == "nightly"

    def test_incremental_filters_to_new_items(self):
        mgr = BackupManager()
        base = mgr.create_backup([{"id": "a"}, {"id": "b"}])
        inc = mgr.create_incremental_backup(
            [{"id": "b"}, {"id": "c"}], last_backup_id=base.backup_id
        )
        assert [i["id"] for i in inc.data] == ["c"]
        assert inc.metadata["type"] == "incremental"
        assert inc.metadata["base"] == base.backup_id

    def test_incremental_no_new_items_creates_empty(self):
        mgr = BackupManager()
        base = mgr.create_backup([{"id": "a"}])
        inc = mgr.create_incremental_backup(
            [{"id": "a"}], last_backup_id=base.backup_id
        )
        assert inc.data == []
        assert inc.metadata["type"] == "incremental"

    def test_incremental_no_base_id_is_full_backup(self):
        mgr = BackupManager()
        e = mgr.create_incremental_backup([{"id": "a"}, {"id": "b"}])
        assert len(e.data) == 2
        assert e.metadata.get("type") != "incremental"

    def test_summary_empty(self):
        mgr = BackupManager()
        s = mgr.get_backup_summary()
        assert s == {
            "total_backups": 0,
            "total_items_backed_up": 0,
            "latest_backup": None,
            "oldest_backup": None,
        }

    def test_summary_populated(self):
        mgr = BackupManager()
        mgr.store.backups["old"] = _entry(
            "old", datetime(2020, 1, 1, tzinfo=UTC), data=[{"id": "a"}]
        )
        mgr.store.backups["new"] = _entry(
            "new", datetime(2022, 1, 1, tzinfo=UTC), data=[{"id": "b"}, {"id": "c"}]
        )
        s = mgr.get_backup_summary()
        assert s["total_backups"] == 2
        assert s["total_items_backed_up"] == 3
        assert s["latest_backup"] == "new"
        assert s["oldest_backup"] == "old"

    def test_cleanup_removes_old_keeps_new(self):
        mgr = BackupManager()
        now = datetime.now(UTC)
        mgr.store.backups["old"] = _entry(
            "old", now - timedelta(days=60), data=[{"id": "a"}]
        )
        mgr.store.backups["new"] = _entry(
            "new", now - timedelta(days=1), data=[{"id": "b"}]
        )
        removed = mgr.cleanup_old_backups(older_than=timedelta(days=30))
        assert removed == 1
        assert "old" not in mgr.store.backups
        assert "new" in mgr.store.backups

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-75: cleanup_old_backups compares raw b.timestamp < cutoff "
            "(backup_manager.py:131) without _normalize_tz, so a backup "
            "imported from a file with a naive ISO timestamp raises "
            "TypeError: can't compare offset-naive and offset-aware "
            "datetimes. _normalize_tz is applied in list_backups/_evict_oldest "
            "but not here. Flip to a hard pin once fixed."
        ),
    )
    def test_cleanup_naive_timestamp_no_typeerror(self):
        # A backup imported from a file with a naive ISO timestamp has a
        # naive datetime; cleanup must normalize it before comparing.
        store = BackupStore()
        store.backups["naive"] = _entry("naive", datetime(2020, 1, 1))
        mgr = BackupManager(store=store)
        removed = mgr.cleanup_old_backups(older_than=timedelta(days=30))
        assert isinstance(removed, int)


class TestRestoreManager:
    """RestoreManager: missing/empty/conflict semantics."""

    def test_restore_from_backup_missing(self):
        rm = RestoreManager()
        r = rm.restore_from_backup("nope")
        assert r.success is False
        assert r.items_restored == 0
        assert r.backup_id == "nope"
        assert any("not found" in e for e in r.errors)

    def test_restore_from_backup_found(self):
        rm = RestoreManager()
        rm.store.add_backup([{"id": "a"}, {"id": "b"}], backup_id="b1")
        r = rm.restore_from_backup("b1")
        assert r.success is True
        assert r.items_restored == 2
        assert r.errors == []

    def test_restore_latest_empty(self):
        rm = RestoreManager()
        r = rm.restore_latest()
        assert r.success is False
        assert r.backup_id == ""
        assert any("No backups" in e for e in r.errors)

    def test_restore_latest_populated(self):
        rm = RestoreManager()
        rm.store.add_backup([{"id": "a"}], backup_id="b1")
        r = rm.restore_latest()
        assert r.success is True
        assert r.items_restored == 1

    def test_restore_items_missing_returns_empty(self):
        assert RestoreManager().restore_items("nope") == []

    def test_restore_items_returns_copies(self):
        rm = RestoreManager()
        rm.store.add_backup([{"id": "a", "title": "t"}], backup_id="b1")
        items = rm.restore_items("b1")
        items[0]["title"] = "MUTATED"
        assert rm.store.get_backup("b1").data[0]["title"] == "t"

    def test_merge_restore_dedups_by_id(self):
        rm = RestoreManager()
        rm.store.add_backup(
            [{"id": "a"}, {"id": "b"}, {"id": "c"}], backup_id="b1"
        )
        existing = [{"id": "b"}, {"id": "d"}]
        merged = rm.merge_restore("b1", existing)
        ids = [i["id"] for i in merged]
        assert ids == ["b", "d", "a", "c"]  # existing order, then new only

    def test_merge_restore_missing_backup_returns_existing(self):
        rm = RestoreManager()
        existing = [{"id": "x"}]
        assert rm.merge_restore("nope", existing) == existing
