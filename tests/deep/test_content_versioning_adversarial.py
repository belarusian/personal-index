"""Adversarial deep tests for content_versioning module.

Tests edge cases: None/empty inputs, unicode, duplicate versioning,
rollback/delete non-existent versions, serialization round-trips.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from personal_index.content_versioning import (
    ContentVersion,
    ContentVersioning,
    create_version,
    get_versions,
)


class TestContentVersionEdgeCases:
    """Edge cases for ContentVersion dataclass."""

    def test_version_with_empty_content(self):
        """Version with empty string content should be valid."""
        v = ContentVersion(version_id="test_v1", content="")
        assert v.version_id == "test_v1"
        assert v.content == ""
        assert v.created_at != ""  # Should have default timestamp

    def test_version_with_none_content(self):
        """Version with None content should be valid (no type coercion)."""
        v = ContentVersion(version_id="test_v1", content=None)
        assert v.content is None

    def test_version_with_unicode_content(self):
        """Version with unicode content should be valid."""
        v = ContentVersion(version_id="test_v1", content="Hello 世界 🌍")
        assert v.content == "Hello 世界 🌍"

    def test_version_with_newlines(self):
        """Version with multiline content should be valid."""
        content = "Line 1\nLine 2\nLine 3"
        v = ContentVersion(version_id="test_v1", content=content)
        assert v.content == content

    def test_version_id_generation(self):
        """Version ID should be generated correctly."""
        v = ContentVersion(version_id="item_v1", content="test")
        assert v.version_id == "item_v1"


class TestContentVersioningEdgeCases:
    """Edge cases for ContentVersioning class."""

    @pytest.fixture
    def versioning(self, tmp_path):
        """Create a ContentVersioning instance with temp storage."""
        storage = str(tmp_path / "versions.json")
        return ContentVersioning(storage_path=storage)

    def test_create_version_empty_item_id(self, versioning):
        """Creating version with empty item_id should work."""
        v = versioning.create_version("", "content")
        assert v.version_id == "_v1"
        versions = versioning.get_versions("")
        assert len(versions) == 1

    def test_create_version_none_item_id(self, versioning):
        """Creating version with None item_id should work (no crash)."""
        v = versioning.create_version(None, "content")
        assert v.version_id == "None_v1"

    def test_create_version_unicode_item_id(self, versioning):
        """Creating version with unicode item_id should work."""
        v = versioning.create_version("item_世界", "content")
        assert v.version_id == "item_世界_v1"
        versions = versioning.get_versions("item_世界")
        assert len(versions) == 1

    def test_create_multiple_versions_same_item(self, versioning):
        """Creating multiple versions of same item should increment version."""
        v1 = versioning.create_version("item", "content1")
        v2 = versioning.create_version("item", "content2")
        v3 = versioning.create_version("item", "content3")
        assert v1.version_id == "item_v1"
        assert v2.version_id == "item_v2"
        assert v3.version_id == "item_v3"
        versions = versioning.get_versions("item")
        assert len(versions) == 3

    def test_get_versions_nonexistent_item(self, versioning):
        """Getting versions of non-existent item should return empty list."""
        versions = versioning.get_versions("nonexistent")
        assert versions == []

    def test_get_version_nonexistent_version(self, versioning):
        """Getting non-existent version should return None."""
        versioning.create_version("item", "content")
        v = versioning.get_version("item", "item_v999")
        assert v is None

    def test_get_version_nonexistent_item(self, versioning):
        """Getting version of non-existent item should return None."""
        v = versioning.get_version("nonexistent", "nonexistent_v1")
        assert v is None

    def test_delete_version_nonexistent(self, versioning):
        """Deleting non-existent version should return False."""
        result = versioning.delete_version("item", "item_v1")
        assert result is False

    def test_delete_version_success(self, versioning):
        """Deleting existing version should return True."""
        versioning.create_version("item", "content")
        result = versioning.delete_version("item", "item_v1")
        assert result is True
        versions = versioning.get_versions("item")
        assert len(versions) == 0

    def test_rollback_to_nonexistent_version(self, versioning):
        """Rolling back to non-existent version should return False."""
        versioning.create_version("item", "content")
        result = versioning.rollback_to("item", "item_v999")
        assert result is False

    def test_rollback_to_nonexistent_item(self, versioning):
        """Rolling back non-existent item should return False."""
        result = versioning.rollback_to("nonexistent", "nonexistent_v1")
        assert result is False

    def test_clear_versions_nonexistent_item(self, versioning):
        """Clearing versions of non-existent item should return False."""
        result = versioning.clear_versions("nonexistent")
        assert result is False

    def test_clear_versions_success(self, versioning):
        """Clearing versions of existing item should return True."""
        versioning.create_version("item", "content1")
        versioning.create_version("item", "content2")
        result = versioning.clear_versions("item")
        assert result is True
        versions = versioning.get_versions("item")
        assert len(versions) == 0


class TestContentVersioningPersistence:
    """Persistence and serialization edge cases."""

    @pytest.fixture
    def versioning(self, tmp_path):
        """Create a ContentVersioning instance with temp storage."""
        storage = str(tmp_path / "versions.json")
        return ContentVersioning(storage_path=storage)

    def test_persistence_roundtrip(self, versioning):
        """Versions should persist across reloads."""
        versioning.create_version("item", "content1")
        versioning.create_version("item", "content2")

        # Reload from storage
        versioning2 = ContentVersioning(storage_path=versioning.storage_path)
        versions = versioning2.get_versions("item")
        assert len(versions) == 2
        assert versions[0].content == "content1"
        assert versions[1].content == "content2"

    def test_persistence_unicode(self, versioning):
        """Unicode content should persist correctly."""
        versioning.create_version("item", "Hello 世界 🌍")
        versioning2 = ContentVersioning(storage_path=versioning.storage_path)
        versions = versioning2.get_versions("item")
        assert versions[0].content == "Hello 世界 🌍"

    def test_persistence_newlines(self, versioning):
        """Multiline content should persist correctly."""
        content = "Line 1\nLine 2\nLine 3"
        versioning.create_version("item", content)
        versioning2 = ContentVersioning(storage_path=versioning.storage_path)
        versions = versioning2.get_versions("item")
        assert versions[0].content == content

    def test_corrupted_storage_file(self, tmp_path):
        """Corrupted storage file should be handled gracefully."""
        storage = str(tmp_path / "versions.json")
        with open(storage, "w") as f:
            f.write("not valid json")
        versioning = ContentVersioning(storage_path=storage)
        # Should not crash, should have empty versions
        versions = versioning.get_versions("item")
        assert versions == []

    def test_empty_storage_file(self, tmp_path):
        """Empty storage file should be handled gracefully."""
        storage = str(tmp_path / "versions.json")
        with open(storage, "w") as f:
            f.write("")
        versioning = ContentVersioning(storage_path=storage)
        versions = versioning.get_versions("item")
        assert versions == []


class TestModuleLevelFunctions:
    """Edge cases for module-level convenience functions."""

    def test_create_version_module_level(self):
        """Module-level create_version should work."""
        v = create_version("test_item", "test content")
        assert v.version_id == "test_item_v1"
        assert v.content == "test content"

    def test_get_versions_module_level(self):
        """Module-level get_versions should work."""
        versions = get_versions("test_item")
        # Should return list (possibly empty)
        assert isinstance(versions, list)
