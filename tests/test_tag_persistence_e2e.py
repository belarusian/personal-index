"""End-to-end tests for tag store persistence."""

from __future__ import annotations

import os

from personal_index.tags import TagStore


class TestTagPersistenceE2E:
    """Test tag store persistence with realistic scenarios."""

    def test_save_and_load(self, tmp_path):
        """Save tags and load them back."""
        path = str(tmp_path / "tags.json")
        store1 = TagStore(store_path=path)
        
        # Add some tags
        store1.create_tag("python", color="#3776AB")
        store1.create_tag("rust", color="#DEA584")
        
        # Verify saved
        assert os.path.exists(path)
        
        # Load new instance
        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        
        assert len(tags) == 2
        names = {t.name for t in tags}
        assert "python" in names
        assert "rust" in names

    def test_persistence_across_instances(self, tmp_path):
        """Tags persist across different instances."""
        path = str(tmp_path / "tags.json")
        
        # First instance
        store1 = TagStore(store_path=path)
        store1.create_tag("test", color="#ff0000")
        del store1
        
        # Second instance
        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        
        assert len(tags) == 1
        assert tags[0].name == "test"

    def test_persistence_with_page_tags(self, tmp_path):
        """Page tags persist correctly."""
        path = str(tmp_path / "tags.json")
        
        store1 = TagStore(store_path=path)
        store1.create_tag("important", color="#ff0000")
        store1.add_tag_to_page("https://example.com/page1", "important")
        
        # Load and verify
        store2 = TagStore(store_path=path)
        tags = store2.get_tags_for_page("https://example.com/page1")
        
        assert len(tags) == 1
        assert tags[0].name == "important"

    def test_persistence_with_multiple_pages(self, tmp_path):
        """Multiple pages can have the same tag."""
        path = str(tmp_path / "tags.json")
        
        store1 = TagStore(store_path=path)
        store1.create_tag("tech", color="#3498db")
        store1.add_tag_to_page("https://example.com/page1", "tech")
        store1.add_tag_to_page("https://example.com/page2", "tech")
        store1.add_tag_to_page("https://example.com/page3", "tech")
        
        # Load and verify
        store2 = TagStore(store_path=path)
        
        assert len(store2.get_tags_for_page("https://example.com/page1")) == 1
        assert len(store2.get_tags_for_page("https://example.com/page2")) == 1
        assert len(store2.get_tags_for_page("https://example.com/page3")) == 1

    def test_persistence_with_remove(self, tmp_path):
        """Removed tags don't persist."""
        path = str(tmp_path / "tags.json")
        
        store1 = TagStore(store_path=path)
        store1.create_tag("keep", color="#00ff00")
        store1.create_tag("remove", color="#ff0000")
        store1.delete_tag("remove")
        
        # Verify removal persisted
        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        
        assert len(tags) == 1
        assert tags[0].name == "keep"

    def test_persistence_with_update(self, tmp_path):
        """Updated tags persist."""
        path = str(tmp_path / "tags.json")
        
        store1 = TagStore(store_path=path)
        store1.create_tag("test", color="#cccccc")
        # Update by deleting and recreating
        store1.delete_tag("test")
        store1.create_tag("test", color="#333333")
        
        # Verify update persisted
        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        
        assert len(tags) == 1
        assert tags[0].color == "#333333"

    def test_empty_file_handling(self, tmp_path):
        """Handle empty file gracefully."""
        path = str(tmp_path / "tags.json")
        
        with open(path, "w") as f:
            f.write("")
        
        store = TagStore(store_path=path)
        assert store.list_tags() == []

    def test_invalid_json_handling(self, tmp_path):
        """Handle invalid JSON gracefully."""
        path = str(tmp_path / "tags.json")
        
        with open(path, "w") as f:
            f.write("{invalid json}")
        
        store = TagStore(store_path=path)
        assert store.list_tags() == []

    def test_large_number_of_tags(self, tmp_path):
        """Handle many tags."""
        path = str(tmp_path / "tags.json")
        store = TagStore(store_path=path)
        
        # Add 100 tags
        for i in range(100):
            store.create_tag(f"tag_{i}", color=f"#{i:06x}")
        
        # Verify all persisted
        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        
        assert len(tags) == 100

    def test_interleaved_operations(self, tmp_path):
        """Multiple operations on same file."""
        path = str(tmp_path / "tags.json")
        
        store1 = TagStore(store_path=path)
        store1.create_tag("a", color="#aaaaaa")
        
        store2 = TagStore(store_path=path)
        store2.create_tag("b", color="#bbbbbb")
        
        store3 = TagStore(store_path=path)
        tags = store3.list_tags()
        
        assert len(tags) == 2
        names = {t.name for t in tags}
        assert "a" in names
        assert "b" in names

    def test_tag_metadata_persistence(self, tmp_path):
        """Tag metadata persists."""
        path = str(tmp_path / "tags.json")
        
        store1 = TagStore(store_path=path)
        store1.create_tag(
            name="important",
            color="#ff0000",
            description="Important content tag"
        )
        
        # Load and verify
        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        
        assert len(tags) == 1
        assert tags[0].name == "important"
        assert tags[0].color == "#ff0000"
        assert tags[0].description == "Important content tag"

    def test_tag_to_from_dict(self, tmp_path):
        """Tag can be serialized and deserialized."""
        path = str(tmp_path / "tags.json")
        
        store1 = TagStore(store_path=path)
        original = store1.create_tag(
            name="test",
            color="#3498db",
            description="Test tag"
        )
        
        # Load new instance
        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        
        assert len(tags) == 1
        assert tags[0].name == original.name
        assert tags[0].color == original.color
