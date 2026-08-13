"""Tests for content archiver."""

from datetime import datetime, timedelta, timezone

from personal_index.content_archive.archiver import (
    ArchiveConfig,
    ContentArchiver,
)


class TestArchiveConfig:
    def test_defaults(self):
        c = ArchiveConfig()
        assert c.days_threshold == 30
        assert c.compression_format == "gzip"
        assert c.max_archive_size_mb == 100

    def test_format_property(self):
        c = ArchiveConfig(compression_format="zlib")
        assert c.format.value == "zlib"


class TestContentArchiver:
    def test_add_item(self):
        a = ContentArchiver()
        a.add_item("id1", "hello")
        item = a.get_item("id1")
        assert item is not None
        assert item.content == "hello"

    def test_get_item_missing(self):
        a = ContentArchiver()
        assert a.get_item("missing") is None

    def test_remove_item(self):
        a = ContentArchiver()
        a.add_item("id1", "hello")
        a.remove_item("id1")
        assert a.get_item("id1") is None

    def test_archive_old(self):
        a = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        a.add_item("id1", "hello", saved_at=old_time)
        archived = a.archive_old(30)
        assert "id1" in archived

    def test_archive_old_keeps_recent(self):
        a = ContentArchiver()
        a.add_item("id1", "hello")
        archived = a.archive_old(30)
        assert archived == []

    def test_restore_item(self):
        a = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        a.add_item("id1", "hello", saved_at=old_time)
        a.archive_old(30)
        result = a.restore_item("id1")
        assert result is True

    def test_restore_active_item(self):
        a = ContentArchiver()
        a.add_item("id1", "hello")
        result = a.restore_item("id1")
        assert result is False

    def test_get_archived_items(self):
        a = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        a.add_item("id1", "hello", saved_at=old_time)
        a.archive_old(30)
        archived = a.get_archived_items()
        assert len(archived) == 1

    def test_delete_archived(self):
        a = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        a.add_item("id1", "hello", saved_at=old_time)
        a.archive_old(30)
        deleted = a.delete_archived()
        assert "id1" in deleted
        assert a.get_item("id1") is None

    def test_get_stats(self):
        a = ContentArchiver()
        a.add_item("id1", "hello")
        stats = a.get_stats()
        assert stats["total_items"] == 1
        assert stats["active_items"] == 1
        assert stats["archived_items"] == 0

    def test_get_stats_with_archived(self):
        a = ContentArchiver()
        a.add_item("id1", "hello")
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        a.add_item("id2", "world", saved_at=old_time)
        a.archive_old(30)
        stats = a.get_stats()
        assert stats["archived_items"] == 1

    def test_export_archived(self):
        import tempfile, json
        a = ContentArchiver()
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        a.add_item("id1", "hello", saved_at=old_time)
        a.archive_old(30)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            a.export_archived(f.name)
            data = json.loads(open(f.name).read())
            assert len(data) == 1
