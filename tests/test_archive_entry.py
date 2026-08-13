"""Tests for archive entry data model."""

from personal_index.content_archive.archive_entry import (
    ArchiveEntry,
    ArchiveStatus,
)


class TestArchiveEntry:
    def test_creation(self):
        e = ArchiveEntry(item_id="id1", content="hello")
        assert e.item_id == "id1"
        assert e.content == "hello"
        assert e.original_size == 5
        assert e.status == ArchiveStatus.ACTIVE

    def test_original_size_computed(self):
        e = ArchiveEntry(item_id="id1", content="test")
        assert e.original_size == 4

    def test_original_size_override(self):
        e = ArchiveEntry(item_id="id1", content="test", original_size=100)
        assert e.original_size == 100

    def test_archive(self):
        e = ArchiveEntry(item_id="id1", content="hello")
        e.archive()
        assert e.status == ArchiveStatus.ARCHIVED
        assert e.archived_at is not None

    def test_restore(self):
        e = ArchiveEntry(item_id="id1", content="hello")
        e.archive()
        e.restore()
        assert e.status == ArchiveStatus.ACTIVE
        assert e.restored_at is not None

    def test_delete(self):
        e = ArchiveEntry(item_id="id1", content="hello")
        e.delete()
        assert e.status == ArchiveStatus.DELETED

    def test_to_dict(self):
        e = ArchiveEntry(item_id="id1", content="hello")
        d = e.to_dict()
        assert d["item_id"] == "id1"
        assert d["content"] == "hello"
        assert d["status"] == "active"
        assert d["original_size"] == 5

    def test_from_dict(self):
        d = {
            "item_id": "id1",
            "content": "hello",
            "original_size": 5,
            "status": "archived",
            "archived_at": "2025-01-01T00:00:00+00:00",
            "restored_at": None,
        }
        e = ArchiveEntry.from_dict(d)
        assert e.item_id == "id1"
        assert e.content == "hello"
        assert e.status == ArchiveStatus.ARCHIVED
        assert e.archived_at == "2025-01-01T00:00:00+00:00"

    def test_from_dict_minimal(self):
        d = {"item_id": "id1"}
        e = ArchiveEntry.from_dict(d)
        assert e.item_id == "id1"
        assert e.content == ""
        assert e.status == ArchiveStatus.ACTIVE

    def test_equality_same(self):
        e1 = ArchiveEntry(item_id="id1", content="hello")
        e2 = ArchiveEntry(item_id="id1", content="hello")
        assert e1 == e2

    def test_equality_different_id(self):
        e1 = ArchiveEntry(item_id="id1", content="hello")
        e2 = ArchiveEntry(item_id="id2", content="hello")
        assert e1 != e2

    def test_equality_different_content(self):
        e1 = ArchiveEntry(item_id="id1", content="hello")
        e2 = ArchiveEntry(item_id="id1", content="world")
        assert e1 != e2

    def test_equality_not_archive_entry(self):
        e = ArchiveEntry(item_id="id1", content="hello")
        assert e != "not an entry"

    def test_unicode_content_size(self):
        e = ArchiveEntry(item_id="id1", content="héllo")
        assert e.original_size == 6

    def test_empty_content(self):
        e = ArchiveEntry(item_id="id1", content="")
        assert e.original_size == 0

    def test_roundtrip(self):
        e = ArchiveEntry(item_id="id1", content="data")
        e.archive()
        d = e.to_dict()
        e2 = ArchiveEntry.from_dict(d)
        assert e2.item_id == e.item_id
        assert e2.content == e.content
        assert e2.status == e.status
