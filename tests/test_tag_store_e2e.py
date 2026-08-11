"""End-to-end tests for tag store operations."""

from __future__ import annotations

import pytest

from personal_index.tags import TagStore


class TestTagStoreE2E:
    """Test tag store with realistic workflows."""

    def test_create_and_list_tags(self, tmp_path):
        """Create tags and verify they are listed."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3776AB")
        store.create_tag("rust", color="#DEA584")
        tags = store.list_tags()
        assert len(tags) == 2
        names = {t.name for t in tags}
        assert "python" in names
        assert "rust" in names

    def test_add_tag_to_page(self, tmp_path):
        """Add a tag to a page and retrieve it."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("important", color="#ff0000")
        store.add_tag_to_page("https://example.com/page1", "important")
        tags = store.get_tags_for_page("https://example.com/page1")
        assert len(tags) == 1
        assert tags[0].name == "important"

    def test_add_multiple_tags_to_page(self, tmp_path):
        """Add multiple tags to a page."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("tech", color="#3498db")
        store.create_tag("tutorial", color="#2ecc71")
        store.add_tag_to_page("https://example.com/page1", "tech")
        store.add_tag_to_page("https://example.com/page1", "tutorial")
        tags = store.get_tags_for_page("https://example.com/page1")
        assert len(tags) == 2
        names = {t.name for t in tags}
        assert "tech" in names
        assert "tutorial" in names

    def test_delete_tag(self, tmp_path):
        """Delete a tag."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("temp", color="#cccccc")
        store.delete_tag("temp")
        tags = store.list_tags()
        assert len(tags) == 0

    def test_persistence_across_instances(self, tmp_path):
        """Tags persist across TagStore instances."""
        path = str(tmp_path / "tags.json")
        store1 = TagStore(store_path=path)
        store1.create_tag("persistent", color="#ff0000")
        del store1

        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        assert len(tags) == 1
        assert tags[0].name == "persistent"

    def test_empty_store(self, tmp_path):
        """Empty store returns empty list."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        assert store.list_tags() == []
        assert store.get_tags_for_page("https://example.com/none") == []
