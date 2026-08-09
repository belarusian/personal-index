"""Tests for content_versioning module."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from personal_index.content_versioning import (
    ContentVersion,
    VersionStore,
    VersionRecord,
)


class TestContentVersion:
    def test_create_version(self):
        version = ContentVersion(
            content_id="test-1",
            version_number=1,
            content="Hello World",
            title="Test Content",
        )
        assert version.content_id == "test-1"
        assert version.version_number == 1
        assert version.content == "Hello World"
        assert version.title == "Test Content"
        assert version.is_pinned is False
        assert version.message == ""

    def test_version_hash(self):
        version = ContentVersion(
            content_id="test-1",
            version_number=1,
            content="Hello World",
        )
        assert len(version.content_hash) == 64  # SHA-256 hex length

    def test_version_to_dict(self):
        version = ContentVersion(
            content_id="test-1",
            version_number=2,
            content="Updated content",
            title="Updated",
            message="Second version",
        )
        d = version.to_dict()
        assert d["content_id"] == "test-1"
        assert d["version_number"] == 2
        assert d["content"] == "Updated content"
        assert d["message"] == "Second version"

    def test_version_from_dict(self):
        data = {
            "content_id": "test-1",
            "version_number": 3,
            "content": "From dict",
            "title": "From Dict",
            "content_hash": "abc123",
            "created_at": "2024-01-01T00:00:00+00:00",
            "message": "Imported",
            "is_pinned": True,
            "metadata": {"key": "value"},
        }
        v = ContentVersion.from_dict(data)
        assert v.content_id == "test-1"
        assert v.version_number == 3
        assert v.is_pinned is True
        assert v.metadata == {"key": "value"}


class TestVersionStore:
    def test_create_store(self):
        store = VersionStore()
        assert store.max_versions == 10
        assert len(store._versions) == 0

    def test_create_store_with_max_versions(self):
        store = VersionStore(max_versions=5)
        assert store.max_versions == 5

    def test_save_version(self):
        store = VersionStore()
        record = store.save_version("doc-1", "Initial content", title="Doc 1")
        assert record.version_number == 1
        assert record.content == "Initial content"
        assert record.content_id == "doc-1"

    def test_save_multiple_versions(self):
        store = VersionStore()
        store.save_version("doc-1", "Version 1")
        store.save_version("doc-1", "Version 2")
        store.save_version("doc-1", "Version 3")
        versions = store.get_versions("doc-1")
        assert len(versions) == 3
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2
        assert versions[2].version_number == 3

    def test_save_version_with_message(self):
        store = VersionStore()
        record = store.save_version("doc-1", "Content", message="Initial commit")
        assert record.message == "Initial commit"

    def test_save_version_with_metadata(self):
        store = VersionStore()
        record = store.save_version(
            "doc-1", "Content",
            metadata={"author": "test", "reviewed": True}
        )
        assert record.metadata == {"author": "test", "reviewed": True}

    def test_get_latest_version(self):
        store = VersionStore()
        store.save_version("doc-1", "V1")
        store.save_version("doc-1", "V2")
        latest = store.get_latest("doc-1")
        assert latest is not None
        assert latest.version_number == 2
        assert latest.content == "V2"

    def test_get_latest_empty(self):
        store = VersionStore()
        latest = store.get_latest("nonexistent")
        assert latest is None

    def test_get_version_by_number(self):
        store = VersionStore()
        store.save_version("doc-1", "V1")
        store.save_version("doc-1", "V2")
        store.save_version("doc-1", "V3")
        v = store.get_version_by_number("doc-1", 2)
        assert v is not None
        assert v.version_number == 2
        assert v.content == "V2"

    def test_get_version_by_number_not_found(self):
        store = VersionStore()
        store.save_version("doc-1", "V1")
        v = store.get_version_by_number("doc-1", 99)
        assert v is None

    def test_max_versions_enforced(self):
        store = VersionStore(max_versions=3)
        for i in range(5):
            store.save_version("doc-1", f"Content {i}")
        versions = store.get_versions("doc-1")
        assert len(versions) == 3
        assert versions[0].version_number == 3
        assert versions[1].version_number == 4
        assert versions[2].version_number == 5

    def test_save_skips_duplicate_content(self):
        store = VersionStore()
        r1 = store.save_version("doc-1", "Same content")
        r2 = store.save_version("doc-1", "Same content")
        assert r1.version_number == r2.version_number
        versions = store.get_versions("doc-1")
        assert len(versions) == 1

    def test_multiple_content_ids(self):
        store = VersionStore()
        store.save_version("doc-1", "Content A")
        store.save_version("doc-2", "Content B")
        assert len(store.get_versions("doc-1")) == 1
        assert len(store.get_versions("doc-2")) == 1
        assert store.get_versions("doc-1")[0].content == "Content A"

    def test_get_all_content_ids(self):
        store = VersionStore()
        store.save_version("doc-1", "A")
        store.save_version("doc-2", "B")
        store.save_version("doc-3", "C")
        ids = store.get_all_content_ids()
        assert set(ids) == {"doc-1", "doc-2", "doc-3"}

    def test_version_count(self):
        store = VersionStore()
        store.save_version("doc-1", "V1")
        store.save_version("doc-1", "V2")
        store.save_version("doc-2", "V1")
        assert store.version_count("doc-1") == 2
        assert store.version_count("doc-2") == 1
        assert store.version_count("nonexistent") == 0

    def test_clear_content(self):
        store = VersionStore()
        store.save_version("doc-1", "V1")
        store.clear("doc-1")
        assert len(store.get_versions("doc-1")) == 0

    def test_clear_all(self):
        store = VersionStore()
        store.save_version("doc-1", "V1")
        store.save_version("doc-2", "V1")
        store.clear_all()
        assert len(store.get_all_content_ids()) == 0

    def test_has_versions(self):
        store = VersionStore()
        assert store.has_versions("doc-1") is False
        store.save_version("doc-1", "V1")
        assert store.has_versions("doc-1") is True

    def test_save_version_returns_record(self):
        store = VersionStore()
        record = store.save_version("doc-1", "Content", title="My Doc")
        assert isinstance(record, VersionRecord)
        assert record.content_id == "doc-1"
        assert record.version_number == 1
        assert record.content == "Content"
        assert record.title == "My Doc"
