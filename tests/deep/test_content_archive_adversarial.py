"""Adversarial deep tests for content_archive module.

Targets: ContentArchiver, ArchiveEntry, Compressor
Edge cases: threshold boundaries, unparseable dates, None dates,
empty data, format mismatches, serialization round-trips, negative thresholds.
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from personal_index.content_archive.archiver import ContentArchiver, ArchiveConfig
from personal_index.content_archive.archive_entry import ArchiveEntry, ArchiveStatus
from personal_index.content_archive.compressor import Compressor, CompressionFormat


class TestArchiveOldThresholdBoundary:
    """Items exactly at the threshold should NOT be archived (strictly before)."""

    def test_item_exactly_at_threshold_not_archived(self):
        archiver = ContentArchiver(days_threshold=30)
        # Item exactly 30 days old - should NOT be archived (strictly before cutoff)
        # Use a fixed timestamp to avoid timing races
        fixed_now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        exactly_30_days_ago = (fixed_now - timedelta(days=30)).isoformat()
        archiver.add_item("exact", "content", saved_at=exactly_30_days_ago)
        # Patch datetime.now to return fixed_now
        import unittest.mock
        with unittest.mock.patch('personal_index.content_archive.archiver.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.fromisoformat = datetime.fromisoformat
            archived = archiver.archive_old()
        assert "exact" not in archived

    def test_item_just_over_threshold_archived(self):
        archiver = ContentArchiver(days_threshold=30)
        # Item 31 days old - should be archived
        thirty_one_days_ago = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        archiver.add_item("over", "content", saved_at=thirty_one_days_ago)
        archived = archiver.archive_old()
        assert "over" in archived

    def test_item_recent_not_archived(self):
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("recent", "content", saved_at=datetime.now(timezone.utc).isoformat())
        archived = archiver.archive_old()
        assert "recent" not in archived


class TestArchiveOldNoneAndUnparseableDates:
    """Items with None or unparseable archived_at should be skipped."""

    def test_item_with_none_date_not_archived(self):
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("no_date", "content")  # saved_at=None by default
        archived = archiver.archive_old()
        assert "no_date" not in archived

    def test_item_with_unparseable_date_not_archived(self):
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("bad_date", "content", saved_at="not-a-date")
        archived = archiver.archive_old()
        assert "bad_date" not in archived

    def test_item_with_empty_string_date_not_archived(self):
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("empty_date", "content", saved_at="")
        archived = archiver.archive_old()
        assert "empty_date" not in archived


class TestArchiveOldNegativeThreshold:
    """Negative threshold should archive everything with a valid date."""

    def test_negative_threshold_archives_all_dated_items(self):
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("old", "content", saved_at="2020-01-01T00:00:00+00:00")
        archiver.add_item("new", "content", saved_at=datetime.now(timezone.utc).isoformat())
        archived = archiver.archive_old(days_threshold=-1)
        assert "old" in archived
        assert "new" in archived

    def test_zero_threshold_archives_all_dated_items(self):
        """BUG: threshold=0 is treated as falsy, falls back to config default (30)."""
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("item", "content", saved_at="2020-01-01T00:00:00+00:00")
        archived = archiver.archive_old(days_threshold=0)
        # With threshold=0, cutoff=now, so all dated items should be archived
        # But the code uses `days_threshold or self.config.days_threshold`
        # which treats 0 as falsy and falls back to 30
        assert "item" in archived, "threshold=0 should archive all dated items (bug: treated as 30)"


class TestArchiveRestoreRoundTrip:
    """Archive then restore should return to active status."""

    def test_archive_then_restore(self):
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("item", "content", saved_at="2020-01-01T00:00:00+00:00")
        archiver.archive_old()
        entry = archiver.get_item("item")
        assert entry.status == ArchiveStatus.ARCHIVED

        restored = archiver.restore_item("item")
        assert restored is True
        entry = archiver.get_item("item")
        assert entry.status == ArchiveStatus.ACTIVE
        assert entry.restored_at is not None

    def test_restore_non_archived_item_returns_false(self):
        archiver = ContentArchiver()
        archiver.add_item("item", "content")
        restored = archiver.restore_item("item")
        assert restored is False

    def test_restore_missing_item_returns_false(self):
        archiver = ContentArchiver()
        restored = archiver.restore_item("missing")
        assert restored is False


class TestDuplicateItemIds:
    """Adding an item with an existing ID should overwrite."""

    def test_duplicate_id_overwrites(self):
        archiver = ContentArchiver()
        archiver.add_item("item", "original")
        archiver.add_item("item", "replacement")
        entry = archiver.get_item("item")
        assert entry.content == "replacement"

    def test_duplicate_id_preserves_date(self):
        archiver = ContentArchiver()
        old_date = "2020-01-01T00:00:00+00:00"
        archiver.add_item("item", "original", saved_at=old_date)
        archiver.add_item("item", "replacement")
        entry = archiver.get_item("item")
        # New add_item creates new entry with None date
        assert entry.archived_at is None


class TestCompressorEdgeCases:
    """Compressor should handle empty data and format mismatches."""

    def test_compress_empty_bytes(self):
        comp = Compressor()
        compressed = comp.compress(b"")
        decompressed = comp.decompress(compressed)
        assert decompressed == b""

    def test_compress_empty_string(self):
        comp = Compressor()
        compressed = comp.compress_text("")
        decompressed = comp.decompress_text(compressed)
        assert decompressed == ""

    def test_format_mismatch_decompress_fails(self):
        comp = Compressor()
        compressed = comp.compress(b"data", CompressionFormat.GZIP)
        with pytest.raises(Exception):
            comp.decompress(compressed, CompressionFormat.ZLIB)

    def test_unicode_round_trip(self):
        comp = Compressor()
        text = "Hello 世界 🌍"
        compressed = comp.compress_text(text)
        decompressed = comp.decompress_text(compressed)
        assert decompressed == text

    def test_compression_ratio_empty(self):
        comp = Compressor()
        ratio = comp.compression_ratio(b"", b"")
        assert ratio == 0.0

    def test_compression_ratio_normal(self):
        comp = Compressor()
        original = b"repeated data " * 100
        compressed = comp.compress(original)
        ratio = comp.compression_ratio(original, compressed)
        assert 0.0 < ratio < 1.0


class TestArchiveEntrySerialization:
    """to_dict/from_dict should round-trip correctly."""

    def test_round_trip(self):
        entry = ArchiveEntry(item_id="test", content="hello")
        entry.archive()
        data = entry.to_dict()
        restored = ArchiveEntry.from_dict(data)
        assert restored.item_id == "test"
        assert restored.content == "hello"
        assert restored.status == ArchiveStatus.ARCHIVED
        assert restored.archived_at is not None

    def test_from_dict_missing_fields(self):
        data = {"item_id": "test"}
        entry = ArchiveEntry.from_dict(data)
        assert entry.item_id == "test"
        assert entry.content == ""
        assert entry.status == ArchiveStatus.ACTIVE

    def test_from_dict_status_string(self):
        data = {"item_id": "test", "status": "archived"}
        entry = ArchiveEntry.from_dict(data)
        assert entry.status == ArchiveStatus.ARCHIVED

    def test_entry_equality(self):
        e1 = ArchiveEntry(item_id="test", content="hello")
        e2 = ArchiveEntry(item_id="test", content="hello")
        e3 = ArchiveEntry(item_id="test", content="world")
        assert e1 == e2
        assert e1 != e3

    def test_entry_original_size_computed(self):
        entry = ArchiveEntry(item_id="test", content="hello")
        assert entry.original_size == len("hello".encode("utf-8"))


class TestArchiveConfig:
    """Config edge cases."""

    def test_invalid_compression_format(self):
        config = ArchiveConfig(compression_format="invalid")
        with pytest.raises(ValueError):
            _ = config.format

    def test_default_config(self):
        config = ArchiveConfig()
        assert config.days_threshold == 30
        assert config.compression_format == "gzip"
        assert config.format == CompressionFormat.GZIP


class TestEndToEndArchiveWorkflow:
    """Full workflow: add items, archive old, restore, verify."""

    def test_full_workflow(self):
        archiver = ContentArchiver(days_threshold=7)
        # Add items with various ages
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        recent = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        archiver.add_item("old1", "old content", saved_at=old)
        archiver.add_item("old2", "old content 2", saved_at=old)
        archiver.add_item("recent1", "recent content", saved_at=recent)
        archiver.add_item("no_date", "no date")

        # Archive old items
        archived = archiver.archive_old()
        assert set(archived) == {"old1", "old2"}

        # Verify statuses
        assert archiver.get_item("old1").status == ArchiveStatus.ARCHIVED
        assert archiver.get_item("old2").status == ArchiveStatus.ARCHIVED
        assert archiver.get_item("recent1").status == ArchiveStatus.ACTIVE
        assert archiver.get_item("no_date").status == ArchiveStatus.ACTIVE

        # Restore one
        assert archiver.restore_item("old1") is True
        assert archiver.get_item("old1").status == ArchiveStatus.ACTIVE

        # Archive again - old1 should not be re-archived (no date after restore)
        archived2 = archiver.archive_old()
        assert "old1" not in archived2
        # old2 is already archived; archive_old() only archives ACTIVE items
        # that are old, not items already in ARCHIVED status
        assert "old2" not in archived2
