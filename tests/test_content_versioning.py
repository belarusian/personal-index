"""Tests for content_versioning module - ContentVersioning class."""

import json
import os

import pytest

from personal_index.content_versioning import (
    ContentVersion,
    ContentVersioning,
)


class TestContentVersion:
    """Tests for the ContentVersion dataclass."""

    def test_create_version(self):
        v = ContentVersion(version_id="v1", content="hello")
        assert v.version_id == "v1"
        assert v.content == "hello"
        assert v.created_at != ""
        assert v.author == ""
        assert v.message == ""

    def test_create_version_with_author(self):
        v = ContentVersion(version_id="v1", content="hello", author="alice")
        assert v.author == "alice"

    def test_create_version_with_message(self):
        v = ContentVersion(version_id="v1", content="hello", message="initial")
        assert v.message == "initial"

    def test_version_sets_timestamp(self):
        v = ContentVersion(version_id="v1", content="test")
        from datetime import datetime
        datetime.fromisoformat(v.created_at)


class TestContentVersioning:
    """Tests for the ContentVersioning class."""

    @pytest.fixture
    def tmp_storage(self, tmp_path):
        return str(tmp_path / "versions.json")

    @pytest.fixture
    def versioning(self, tmp_storage):
        return ContentVersioning(storage_path=tmp_storage)

    # -- create_version() --
    def test_create_version_returns_version(self, versioning):
        v = versioning.create_version("item-1", "content v1")
        assert isinstance(v, ContentVersion)
        assert v.content == "content v1"

    def test_create_version_id_format(self, versioning):
        v = versioning.create_version("item-1", "content v1")
        assert v.version_id == "item-1_v1"

    def test_create_version_increments_id(self, versioning):
        v1 = versioning.create_version("item-1", "first")
        v2 = versioning.create_version("item-1", "second")
        assert v1.version_id == "item-1_v1"
        assert v2.version_id == "item-1_v2"

    def test_create_version_with_author_and_message(self, versioning):
        v = versioning.create_version("item-1", "content", author="bob", message="fix typo")
        assert v.author == "bob"
        assert v.message == "fix typo"

    def test_create_version_no_id_collision_after_delete(self, versioning):
        versioning.create_version("item-1", "a")  # item-1_v1
        versioning.create_version("item-1", "b")  # item-1_v2
        assert versioning.delete_version("item-1", "item-1_v1") is True
        v3 = versioning.create_version("item-1", "c")
        ids = [v.version_id for v in versioning.get_versions("item-1")]
        assert ids == ["item-1_v2", "item-1_v3"]
        assert len(ids) == len(set(ids))
        assert v3.version_id == "item-1_v3"

    def test_create_version_multiple_items(self, versioning):
        versioning.create_version("item-1", "content A")
        versioning.create_version("item-2", "content B")
        assert len(versioning.get_versions("item-1")) == 1
        assert len(versioning.get_versions("item-2")) == 1

    # -- get_versions() --
    def test_get_versions_empty(self, versioning):
        assert versioning.get_versions("nonexistent") == []

    def test_get_versions_returns_list(self, versioning):
        versioning.create_version("item-1", "content")
        versions = versioning.get_versions("item-1")
        assert isinstance(versions, list)
        assert len(versions) == 1

    def test_get_versions_multiple(self, versioning):
        versioning.create_version("item-1", "v1")
        versioning.create_version("item-1", "v2")
        versioning.create_version("item-1", "v3")
        assert len(versioning.get_versions("item-1")) == 3

    # -- get_latest() --
    def test_get_latest_version(self, versioning):
        versioning.create_version("item-1", "first")
        versioning.create_version("item-1", "second")
        versioning.create_version("item-1", "third")
        versions = versioning.get_versions("item-1")
        latest = versions[-1]
        assert latest.content == "third"
        assert latest.version_id == "item-1_v3"

    # -- rollback_to() --
    def test_rollback_to_version(self, versioning):
        versioning.create_version("item-1", "v1")
        versioning.create_version("item-1", "v2")
        versioning.create_version("item-1", "v3")
        # Rollback to v1
        versioning.rollback_to("item-1", "item-1_v1")
        versions = versioning.get_versions("item-1")
        # After rollback, latest should be the rollback version
        assert versions[-1].content == "v1"

    def test_rollback_to_nonexistent(self, versioning):
        versioning.create_version("item-1", "v1")
        result = versioning.rollback_to("item-1", "item-1_v999")
        assert result is False

    # -- delete_version() --
    def test_delete_version(self, versioning):
        versioning.create_version("item-1", "v1")
        versioning.create_version("item-1", "v2")
        assert versioning.delete_version("item-1", "item-1_v1") is True
        assert len(versioning.get_versions("item-1")) == 1

    def test_delete_version_nonexistent(self, versioning):
        versioning.create_version("item-1", "v1")
        assert versioning.delete_version("item-1", "item-1_v999") is False

    def test_delete_version_preserves_others(self, versioning):
        versioning.create_version("item-1", "v1")
        versioning.create_version("item-1", "v2")
        versioning.create_version("item-1", "v3")
        versioning.delete_version("item-1", "item-1_v2")
        versions = versioning.get_versions("item-1")
        ids = [v.version_id for v in versions]
        assert "item-1_v1" in ids
        assert "item-1_v2" not in ids
        assert "item-1_v3" in ids

    # -- version comparison --
    def test_version_ordering(self, versioning):
        versioning.create_version("item-1", "first")
        versioning.create_version("item-1", "second")
        versions = versioning.get_versions("item-1")
        assert versions[0].version_id == "item-1_v1"
        assert versions[1].version_id == "item-1_v2"

    def test_version_content_differs(self, versioning):
        versioning.create_version("item-1", "original")
        versioning.create_version("item-1", "updated")
        versions = versioning.get_versions("item-1")
        assert versions[0].content == "original"
        assert versions[1].content == "updated"

    # -- persistence --
    def test_persistence_saves(self, versioning, tmp_storage):
        versioning.create_version("item-1", "content")
        assert os.path.exists(tmp_storage)
        with open(tmp_storage) as f:
            data = json.load(f)
        assert "item-1" in data
        assert len(data["item-1"]) == 1

    def test_persistence_loads(self, tmp_storage):
        data = {
            "item-1": [
                {
                    "version_id": "item-1_v1",
                    "content": "persisted",
                    "created_at": "2024-01-01T00:00:00",
                    "author": "test",
                    "message": "loaded",
                }
            ]
        }
        with open(tmp_storage, "w") as f:
            json.dump(data, f)
        v = ContentVersioning(storage_path=tmp_storage)
        versions = v.get_versions("item-1")
        assert len(versions) == 1
        assert versions[0].content == "persisted"

    # -- clear_versions() --
    def test_clear_versions(self, versioning):
        versioning.create_version("item-1", "v1")
        versioning.create_version("item-1", "v2")
        versioning.clear_versions("item-1")
        assert versioning.get_versions("item-1") == []

    def test_clear_versions_nonexistent(self, versioning):
        assert versioning.clear_versions("nonexistent") is False

    # -- get_version() --
    def test_get_specific_version(self, versioning):
        versioning.create_version("item-1", "v1")
        versioning.create_version("item-1", "v2")
        v = versioning.get_version("item-1", "item-1_v2")
        assert v is not None
        assert v.content == "v2"

    def test_get_specific_version_not_found(self, versioning):
        versioning.create_version("item-1", "v1")
        v = versioning.get_version("item-1", "item-1_v999")
        assert v is None

    # -- _load() with non-dict JSON (TICKET-262) --
    def test_load_null_json(self, tmp_storage):
        """Storage file containing JSON null should not crash."""
        with open(tmp_storage, "w") as f:
            json.dump(None, f)
        v = ContentVersioning(storage_path=tmp_storage)
        assert v.get_versions("item-1") == []

    def test_load_list_json(self, tmp_storage):
        """Storage file containing a JSON list should not crash."""
        with open(tmp_storage, "w") as f:
            json.dump([1, 2, 3], f)
        v = ContentVersioning(storage_path=tmp_storage)
        assert v.get_versions("item-1") == []

    def test_load_number_json(self, tmp_storage):
        """Storage file containing a JSON number should not crash."""
        with open(tmp_storage, "w") as f:
            json.dump(42, f)
        v = ContentVersioning(storage_path=tmp_storage)
        assert v.get_versions("item-1") == []
