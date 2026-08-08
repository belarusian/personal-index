"""Tests for tag/label system."""

from __future__ import annotations

import tempfile

import pytest

from personal_index.tags import Tag, TagStore


class TestTag:
    """Tests for Tag dataclass."""

    def test_tag_creation(self):
        tag = Tag(name="important", color="#ff0000", description="Important pages")
        assert tag.name == "important"
        assert tag.color == "#ff0000"
        assert tag.description == "Important pages"

    def test_tag_default_color(self):
        tag = Tag(name="test")
        assert tag.color == "#3498db"

    def test_tag_hash(self):
        tag1 = Tag(name="test")
        tag2 = Tag(name="test")
        assert hash(tag1) == hash(tag2)

    def test_tag_equality(self):
        tag1 = Tag(name="test")
        tag2 = Tag(name="test")
        tag3 = Tag(name="other")
        assert tag1 == tag2
        assert tag1 != tag3


class TestTagStore:
    """Tests for TagStore class."""

    def setup_method(self):
        self.store = TagStore()

    def test_create_tag(self):
        tag = self.store.create_tag("important", color="#ff0000")
        assert tag.name == "important"
        assert tag.color == "#ff0000"

    def test_get_tag(self):
        self.store.create_tag("test")
        tag = self.store.get_tag("test")
        assert tag is not None
        assert tag.name == "test"

    def test_get_nonexistent_tag(self):
        assert self.store.get_tag("nonexistent") is None

    def test_list_tags(self):
        self.store.create_tag("tag1")
        self.store.create_tag("tag2")
        tags = self.store.list_tags()
        assert len(tags) == 2

    def test_delete_tag(self):
        self.store.create_tag("to_delete")
        assert self.store.delete_tag("to_delete") is True
        assert self.store.get_tag("to_delete") is None

    def test_delete_nonexistent_tag(self):
        assert self.store.delete_tag("nonexistent") is False

    def test_add_tag_to_page(self):
        self.store.create_tag("important")
        assert self.store.add_tag_to_page("http://example.com", "important") is True

    def test_add_nonexistent_tag_to_page(self):
        assert self.store.add_tag_to_page("http://example.com", "nonexistent") is False

    def test_remove_tag_from_page(self):
        self.store.create_tag("important")
        self.store.add_tag_to_page("http://example.com", "important")
        assert self.store.remove_tag_from_page("http://example.com", "important") is True

    def test_get_tags_for_page(self):
        self.store.create_tag("tag1")
        self.store.create_tag("tag2")
        self.store.add_tag_to_page("http://example.com", "tag1")
        self.store.add_tag_to_page("http://example.com", "tag2")
        tags = self.store.get_tags_for_page("http://example.com")
        assert len(tags) == 2

    def test_get_tags_for_untagged_page(self):
        tags = self.store.get_tags_for_page("http://example.com")
        assert tags == []

    def test_get_pages_for_tag(self):
        self.store.create_tag("important")
        self.store.add_tag_to_page("http://a.com", "important")
        self.store.add_tag_to_page("http://b.com", "important")
        pages = self.store.get_pages_for_tag("important")
        assert "http://a.com" in pages
        assert "http://b.com" in pages

    def test_get_pages_for_nonexistent_tag(self):
        assert self.store.get_pages_for_tag("nonexistent") == []

    def test_search_by_tag(self):
        self.store.create_tag("tech")
        self.store.add_tag_to_page("http://tech.com", "tech")
        results = self.store.search_by_tag("tech")
        assert "http://tech.com" in results

    def test_tag_count(self):
        self.store.create_tag("tag1")
        self.store.create_tag("tag2")
        assert self.store.get_tag_count() == 2

    def test_tagged_page_count(self):
        self.store.create_tag("tag1")
        self.store.add_tag_to_page("http://a.com", "tag1")
        assert self.store.get_tagged_page_count() == 1

    def test_clear(self):
        self.store.create_tag("tag1")
        self.store.add_tag_to_page("http://a.com", "tag1")
        self.store.clear()
        assert self.store.get_tag_count() == 0
        assert self.store.get_tagged_page_count() == 0

    def test_delete_tag_removes_from_pages(self):
        self.store.create_tag("tag1")
        self.store.add_tag_to_page("http://a.com", "tag1")
        self.store.delete_tag("tag1")
        assert self.store.get_tags_for_page("http://a.com") == []

    def test_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TagStore(store_path=f.name)
            store.create_tag("persistent", color="#ff0000")
            store.add_tag_to_page("http://example.com", "persistent")

        # Reload
        store2 = TagStore(store_path=f.name)
        tag = store2.get_tag("persistent")
        assert tag is not None
        assert tag.color == "#ff0000"
        assert "http://example.com" in store2.get_pages_for_tag("persistent")

    def test_multiple_tags_per_page(self):
        self.store.create_tag("tag1")
        self.store.create_tag("tag2")
        self.store.create_tag("tag3")
        self.store.add_tag_to_page("http://example.com", "tag1")
        self.store.add_tag_to_page("http://example.com", "tag2")
        self.store.add_tag_to_page("http://example.com", "tag3")
        tags = self.store.get_tags_for_page("http://example.com")
        assert len(tags) == 3
