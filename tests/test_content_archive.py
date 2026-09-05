"""Tests for content_archive module - compress old content."""

import os
import tempfile
from datetime import datetime, timedelta, timezone

from personal_index.content_archive.archive_entry import ArchiveEntry, ArchiveStatus
from personal_index.content_archive.archiver import ContentArchiver
from personal_index.content_archive.compressor import CompressionFormat, Compressor

# ── ArchiveEntry tests ─────────────────────────────────────

class TestArchiveEntry:
    def test_create_entry(self):
        entry = ArchiveEntry(
            item_id="id1",
            content="test content",
            original_size=100,
        )
        assert entry.item_id == "id1"
        assert entry.content == "test content"
        assert entry.original_size == 100
        assert entry.status == ArchiveStatus.ACTIVE

    def test_entry_to_archived(self):
        entry = ArchiveEntry(item_id="id1", content="data")
        entry.archive()
        assert entry.status == ArchiveStatus.ARCHIVED
        assert entry.archived_at is not None

    def test_entry_to_restored(self):
        entry = ArchiveEntry(item_id="id1", content="data")
        entry.archive()
        entry.restore()
        assert entry.status == ArchiveStatus.ACTIVE

    def test_entry_to_dict(self):
        entry = ArchiveEntry(item_id="id1", content="data", original_size=50)
        d = entry.to_dict()
        assert d["item_id"] == "id1"
        assert d["content"] == "data"

    def test_entry_from_dict(self):
        d = {"item_id": "id2", "content": "restored", "original_size": 30, "status": "active"}
        entry = ArchiveEntry.from_dict(d)
        assert entry.item_id == "id2"
        assert entry.status == ArchiveStatus.ACTIVE

    def test_entry_equality(self):
        e1 = ArchiveEntry(item_id="a", content="x")
        e2 = ArchiveEntry(item_id="a", content="x")
        assert e1 == e2

    def test_entry_inequality(self):
        e1 = ArchiveEntry(item_id="a", content="x")
        e2 = ArchiveEntry(item_id="b", content="x")
        assert e1 != e2


class TestArchiveStatus:
    def test_status_values(self):
        assert ArchiveStatus.ACTIVE.value == "active"
        assert ArchiveStatus.ARCHIVED.value == "archived"
        assert ArchiveStatus.DELETED.value == "deleted"

    def test_status_count(self):
        assert len(ArchiveStatus) == 3


# ── Compressor tests ───────────────────────────────────────

class TestCompressor:
    def test_compress_gzip(self):
        comp = Compressor()
        data = b"hello world" * 100
        compressed = comp.compress(data, CompressionFormat.GZIP)
        assert len(compressed) < len(data)

    def test_decompress_gzip(self):
        comp = Compressor()
        original = b"test data for compression" * 50
        compressed = comp.compress(original, CompressionFormat.GZIP)
        decompressed = comp.decompress(compressed, CompressionFormat.GZIP)
        assert decompressed == original

    def test_compress_empty(self):
        comp = Compressor()
        compressed = comp.compress(b"", CompressionFormat.GZIP)
        decompressed = comp.decompress(compressed, CompressionFormat.GZIP)
        assert decompressed == b""

    def test_compression_ratio(self):
        comp = Compressor()
        data = b"a" * 10000
        compressed = comp.compress(data, CompressionFormat.GZIP)
        ratio = comp.compression_ratio(data, compressed)
        assert ratio < 0.5

    def test_compress_string(self):
        comp = Compressor()
        text = "hello world" * 100
        compressed = comp.compress_text(text, CompressionFormat.GZIP)
        assert isinstance(compressed, bytes)

    def test_decompress_to_string(self):
        comp = Compressor()
        text = "hello world" * 100
        compressed = comp.compress_text(text, CompressionFormat.GZIP)
        result = comp.decompress_text(compressed, CompressionFormat.GZIP)
        assert result == text

    def test_format_values(self):
        assert CompressionFormat.GZIP.value == "gzip"
        assert CompressionFormat.ZLIB.value == "zlib"

    def test_compress_zlib(self):
        comp = Compressor()
        data = b"test data" * 100
        compressed = comp.compress(data, CompressionFormat.ZLIB)
        decompressed = comp.decompress(compressed, CompressionFormat.ZLIB)
        assert decompressed == data

    def test_roundtrip(self):
        comp = Compressor()
        original = "The quick brown fox jumps over the lazy dog" * 100
        compressed = comp.compress_text(original, CompressionFormat.GZIP)
        result = comp.decompress_text(compressed, CompressionFormat.GZIP)
        assert result == original

    def test_compression_stats(self):
        comp = Compressor()
        data = b"x" * 5000
        compressed = comp.compress(data, CompressionFormat.GZIP)
        stats = comp.get_stats(data, compressed)
        assert "original_size" in stats
        assert "compressed_size" in stats
        assert "ratio" in stats


# ── ContentArchiver tests ──────────────────────────────────

class TestContentArchiver:
    def test_add_and_archive(self):
        archiver = ContentArchiver()
        archiver.add_item("id1", "some content", saved_at=datetime.now(timezone.utc).isoformat())
        assert archiver.get_item("id1") is not None

    def test_archive_old_items(self):
        archiver = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        archiver.add_item("id1", "old content", saved_at=old_time)
        archiver.add_item("id2", "new content", saved_at=datetime.now(timezone.utc).isoformat())
        archived = archiver.archive_old(days_threshold=30)
        assert len(archived) >= 1

    def test_archive_old_no_saved_at_never_archived(self):
        """Pinning: item added without saved_at is never archived."""
        archiver = ContentArchiver()
        archiver.add_item("no_ts", "content")  # saved_at=None default
        old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        archiver.add_item("old_ts", "content", saved_at=old_time)
        archived = archiver.archive_old(days_threshold=30)
        assert "no_ts" not in archived
        assert "old_ts" in archived

    def test_archive_empty(self):
        archiver = ContentArchiver()
        archived = archiver.archive_old(days_threshold=30)
        assert len(archived) == 0

    def test_restore_item(self):
        archiver = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        archiver.add_item("id1", "old content", saved_at=old_time)
        archiver.archive_old(days_threshold=30)
        archiver.restore_item("id1")
        item = archiver.get_item("id1")
        assert item is not None

    def test_get_archived_items(self):
        archiver = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        archiver.add_item("id1", "old", saved_at=old_time)
        archiver.archive_old(days_threshold=30)
        archived = archiver.get_archived_items()
        assert len(archived) >= 1

    def test_archive_config(self):
        archiver = ContentArchiver(days_threshold=60, compression_format="gzip")
        assert archiver.config.days_threshold == 60

    def test_get_stats(self):
        archiver = ContentArchiver()
        archiver.add_item("id1", "content1")
        archiver.add_item("id2", "content2")
        stats = archiver.get_stats()
        assert "total_items" in stats
        assert stats["total_items"] == 2

    def test_delete_archived(self):
        archiver = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        archiver.add_item("id1", "old", saved_at=old_time)
        archiver.archive_old(days_threshold=30)
        deleted = archiver.delete_archived()
        assert len(deleted) >= 1

    def test_archive_to_file(self):
        archiver = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        archiver.add_item("id1", "old content", saved_at=old_time)
        archiver.archive_old(days_threshold=30)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            archiver.export_archived(f.name)
            assert os.path.exists(f.name)
            os.unlink(f.name)

    def test_remove_item(self):
        archiver = ContentArchiver()
        archiver.add_item("id1", "content")
        archiver.remove_item("id1")
        assert archiver.get_item("id1") is None
