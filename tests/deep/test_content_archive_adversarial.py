"""Adversarial deep tests for content_archive subsystem.

Targets: ArchiveEntry dataclass, ContentArchiver lifecycle,
round-trips, status transitions, edge-case inputs.
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from personal_index.content_archive.archive_entry import ArchiveEntry, ArchiveStatus
from personal_index.content_archive.archiver import ContentArchiver


# --- ArchiveEntry dataclass edge cases ---

class TestArchiveEntryEdgeCases:
    def test_empty_content(self):
        entry = ArchiveEntry(item_id="e1", content="")
        assert entry.original_size == 0
        assert entry.status == ArchiveStatus.ACTIVE

    def test_unicode_content_size(self):
        entry = ArchiveEntry(item_id="e2", content="héllo 🌍")
        # UTF-8 bytes: héllo = 5 bytes, space = 1, 🌍 = 4 bytes
        assert entry.original_size == 11

    def test_none_archived_at_default(self):
        entry = ArchiveEntry(item_id="e3", content="test")
        assert entry.archived_at is None
        assert entry.restored_at is None

    def test_explicit_original_size_overrides(self):
        entry = ArchiveEntry(item_id="e4", content="test", original_size=999)
        assert entry.original_size == 999

    def test_zero_original_size_computed(self):
        entry = ArchiveEntry(item_id="e5", content="test", original_size=0)
        assert entry.original_size == 4  # computed from content


# --- Status transitions ---

class TestStatusTransitions:
    def test_archive_sets_timestamp(self):
        entry = ArchiveEntry(item_id="t1", content="test")
        entry.archive()
        assert entry.status == ArchiveStatus.ARCHIVED
        assert entry.archived_at is not None

    def test_restore_sets_timestamp(self):
        entry = ArchiveEntry(item_id="t2", content="test")
        entry.archive()
        entry.restore()
        assert entry.status == ArchiveStatus.ACTIVE
        assert entry.restored_at is not None

    def test_delete_status(self):
        entry = ArchiveEntry(item_id="t3", content="test")
        entry.delete()
        assert entry.status == ArchiveStatus.DELETED

    def test_restore_non_archived_no_error(self):
        entry = ArchiveEntry(item_id="t4", content="test")
        entry.restore()  # should not raise
        assert entry.status == ArchiveStatus.ACTIVE

    def test_archive_already_archived(self):
        entry = ArchiveEntry(item_id="t5", content="test")
        entry.archive()
        entry.archive()  # idempotent
        assert entry.status == ArchiveStatus.ARCHIVED


# --- to_dict / from_dict round-trips ---

class TestSerializationRoundTrips:
    def test_basic_round_trip(self):
        entry = ArchiveEntry(item_id="r1", content="hello")
        data = entry.to_dict()
        restored = ArchiveEntry.from_dict(data)
        assert restored.item_id == "r1"
        assert restored.content == "hello"
        assert restored.status == ArchiveStatus.ACTIVE

    def test_round_trip_after_archive(self):
        entry = ArchiveEntry(item_id="r2", content="world")
        entry.archive()
        data = entry.to_dict()
        restored = ArchiveEntry.from_dict(data)
        assert restored.status == ArchiveStatus.ARCHIVED
        assert restored.archived_at is not None

    def test_from_dict_missing_content(self):
        data = {"item_id": "r3"}
        entry = ArchiveEntry.from_dict(data)
        assert entry.content == ""

    def test_from_dict_missing_original_size(self):
        data = {"item_id": "r4", "content": "test"}
        entry = ArchiveEntry.from_dict(data)
        assert entry.original_size == 4  # computed

    def test_from_dict_status_string(self):
        data = {"item_id": "r5", "content": "test", "status": "archived"}
        entry = ArchiveEntry.from_dict(data)
        assert entry.status == ArchiveStatus.ARCHIVED

    def test_from_dict_status_enum(self):
        data = {"item_id": "r6", "content": "test", "status": ArchiveStatus.ACTIVE}
        entry = ArchiveEntry.from_dict(data)
        assert entry.status == ArchiveStatus.ACTIVE

    def test_from_dict_extra_fields_ignored(self):
        data = {
            "item_id": "r7",
            "content": "test",
            "extra_field": "ignored",
            "another": 123,
        }
        entry = ArchiveEntry.from_dict(data)
        assert entry.item_id == "r7"

    def test_json_round_trip(self):
        entry = ArchiveEntry(item_id="r8", content="json test")
        entry.archive()
        json_str = json.dumps(entry.to_dict())
        data = json.loads(json_str)
        restored = ArchiveEntry.from_dict(data)
        assert restored.item_id == "r8"
        assert restored.status == ArchiveStatus.ARCHIVED


# --- __eq__ behavior ---

class TestEquality:
    def test_same_id_same_content_equal(self):
        e1 = ArchiveEntry(item_id="eq1", content="same")
        e2 = ArchiveEntry(item_id="eq1", content="same")
        assert e1 == e2

    def test_same_id_different_content_not_equal(self):
        e1 = ArchiveEntry(item_id="eq2", content="a")
        e2 = ArchiveEntry(item_id="eq2", content="b")
        assert e1 != e2

    def test_different_id_same_content_not_equal(self):
        e1 = ArchiveEntry(item_id="eq3", content="same")
        e2 = ArchiveEntry(item_id="eq4", content="same")
        assert e1 != e2

    def test_not_equal_to_non_entry(self):
        e1 = ArchiveEntry(item_id="eq5", content="test")
        assert e1 != "not an entry"
        assert e1 != None
        assert e1 != 42


# --- ContentArchiver edge cases ---

class TestArchiverEdgeCases:
    def test_empty_archiver_stats(self):
        archiver = ContentArchiver()
        stats = archiver.get_stats()
        assert stats["total_items"] == 0
        assert stats["active_items"] == 0
        assert stats["archived_items"] == 0
        assert stats["deleted_items"] == 0

    def test_archive_old_no_items(self):
        archiver = ContentArchiver()
        archived = archiver.archive_old()
        assert archived == []

    def test_restore_nonexistent_item(self):
        archiver = ContentArchiver()
        result = archiver.restore_item("nonexistent")
        assert result is False

    def test_get_nonexistent_item(self):
        archiver = ContentArchiver()
        result = archiver.get_item("nonexistent")
        assert result is None

    def test_remove_nonexistent_item(self):
        archiver = ContentArchiver()
        archiver.remove_item("nonexistent")  # should not raise

    def test_delete_archived_empty(self):
        archiver = ContentArchiver()
        deleted = archiver.delete_archived()
        assert deleted == []

    def test_archive_old_negative_days(self):
        archiver = ContentArchiver()
        archiver.add_item("neg1", "test", saved_at="2020-01-01T00:00:00+00:00")
        # Negative threshold means cutoff is in the future, so EVERYTHING archives
        archived = archiver.archive_old(days_threshold=-1)
        assert "neg1" in archived

    @pytest.mark.xfail(strict=True, reason="QA-54: days_threshold=0 falls back to default due to falsy evaluation")
    def test_archive_old_zero_days(self):
        archiver = ContentArchiver()
        # Item from yesterday should archive with 0-day threshold
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        archiver.add_item("zero1", "test", saved_at=yesterday.isoformat())
        archived = archiver.archive_old(days_threshold=0)
        assert "zero1" in archived

    def test_archive_old_default_threshold(self):
        archiver = ContentArchiver(days_threshold=30)
        # Item from 60 days ago should archive
        old = datetime.now(timezone.utc) - timedelta(days=60)
        archiver.add_item("old1", "test", saved_at=old.isoformat())
        # Item from 10 days ago should not
        recent = datetime.now(timezone.utc) - timedelta(days=10)
        archiver.add_item("new1", "test", saved_at=recent.isoformat())
        archived = archiver.archive_old()
        assert "old1" in archived
        assert "new1" not in archived

    def test_archive_old_no_saved_at_never_archives(self):
        archiver = ContentArchiver(days_threshold=0)
        archiver.add_item("no_ts", "test")  # saved_at=None
        archived = archiver.archive_old()
        assert archived == []

    def test_archive_old_unparseable_timestamp(self):
        archiver = ContentArchiver(days_threshold=0)
        archiver.add_item("bad_ts", "test", saved_at="not-a-date")
        archived = archiver.archive_old()
        assert archived == []  # silently skipped

    def test_stats_after_operations(self):
        archiver = ContentArchiver()
        archiver.add_item("s1", "test1")
        archiver.add_item("s2", "test2")
        archiver.add_item("s3", "test3")

        stats = archiver.get_stats()
        assert stats["total_items"] == 3
        assert stats["active_items"] == 3

        # Archive one
        entry = archiver.get_item("s1")
        entry.archive()
        stats = archiver.get_stats()
        assert stats["archived_items"] == 1
        assert stats["active_items"] == 2

        # Delete archived
        deleted = archiver.delete_archived()
        assert "s1" in deleted
        stats = archiver.get_stats()
        assert stats["total_items"] == 2
        assert stats["archived_items"] == 0

    def test_export_archived_empty(self):
        archiver = ContentArchiver()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            archiver.export_archived(filepath)
            content = Path(filepath).read_text()
            assert content == "[]"
        finally:
            Path(filepath).unlink()

    def test_export_archived_with_items(self):
        archiver = ContentArchiver()
        archiver.add_item("exp1", "test content")
        entry = archiver.get_item("exp1")
        entry.archive()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            archiver.export_archived(filepath)
            content = Path(filepath).read_text()
            data = json.loads(content)
            assert len(data) == 1
            assert data[0]["item_id"] == "exp1"
        finally:
            Path(filepath).unlink()

    def test_compression_format_validation(self):
        archiver = ContentArchiver(compression_format="gzip")
        assert archiver.config.format.value == "gzip"

    def test_duplicate_item_id_overwrites(self):
        archiver = ContentArchiver()
        archiver.add_item("dup1", "first")
        archiver.add_item("dup1", "second")
        entry = archiver.get_item("dup1")
        assert entry.content == "second"


# --- End-to-end CLI-style workflow ---

class TestEndToEndWorkflow:
    def test_full_lifecycle(self):
        """Add items, archive old ones, restore, delete."""
        archiver = ContentArchiver(days_threshold=7)

        # Add items with different ages
        old_date = datetime.now(timezone.utc) - timedelta(days=14)
        recent_date = datetime.now(timezone.utc) - timedelta(days=2)

        archiver.add_item("old_item", "old content", saved_at=old_date.isoformat())
        archiver.add_item("new_item", "new content", saved_at=recent_date.isoformat())

        # Archive old items
        archived_ids = archiver.archive_old()
        assert "old_item" in archived_ids
        assert "new_item" not in archived_ids

        # Verify status
        old_entry = archiver.get_item("old_item")
        new_entry = archiver.get_item("new_item")
        assert old_entry.status == ArchiveStatus.ARCHIVED
        assert new_entry.status == ArchiveStatus.ACTIVE

        # Restore old item
        restored = archiver.restore_item("old_item")
        assert restored is True
        assert old_entry.status == ArchiveStatus.ACTIVE

        # Archive again and delete
        old_entry.archive()
        deleted_ids = archiver.delete_archived()
        assert "old_item" in deleted_ids
        assert archiver.get_item("old_item") is None
