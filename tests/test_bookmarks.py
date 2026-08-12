"""Tests for bookmark management module."""

from __future__ import annotations

import os

import pytest

from personal_index.bookmarks import (
    Bookmark,
    BookmarkManager,
)


class TestBookmark:
    """Tests for Bookmark dataclass."""

    def test_create_bookmark(self):
        b = Bookmark(url="http://example.com")
        assert b.url == "http://example.com"
        assert b.category == "uncategorized"
        assert b.is_favorite is False
        assert b.tags == []

    def test_create_bookmark_with_fields(self):
        b = Bookmark(
            url="http://example.com",
            title="Example",
            description="A test site",
            category="tech",
            tags=["test", "example"],
            is_favorite=True,
        )
        assert b.title == "Example"
        assert b.description == "A test site"
        assert b.category == "tech"
        assert b.tags == ["test", "example"]
        assert b.is_favorite is True

    def test_timestamps_auto_set(self):
        b = Bookmark(url="http://example.com")
        assert b.created_at
        assert b.updated_at
        assert b.created_at == b.updated_at

    def test_to_dict(self):
        b = Bookmark(
            url="http://example.com",
            title="Test",
            tags=["a", "b"],
            is_favorite=True,
        )
        d = b.to_dict()
        assert d["url"] == "http://example.com"
        assert d["title"] == "Test"
        assert d["tags"] == ["a", "b"]
        assert d["is_favorite"] is True

    def test_from_dict(self):
        data = {
            "url": "http://example.com",
            "title": "Test",
            "description": "Desc",
            "category": "tech",
            "tags": ["a"],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "is_favorite": True,
        }
        b = Bookmark.from_dict(data)
        assert b.url == "http://example.com"
        assert b.title == "Test"
        assert b.is_favorite is True

    def test_from_dict_defaults(self):
        data = {"url": "http://example.com"}
        b = Bookmark.from_dict(data)
        assert b.title == ""
        assert b.category == "uncategorized"
        assert b.tags == []


class TestBookmarkManager:
    """Tests for BookmarkManager class."""

    def setup_method(self):
        self.manager = BookmarkManager()

    def test_add_bookmark(self):
        b = Bookmark(url="http://example.com", title="Example")
        result = self.manager.add(b)
        assert self.manager.count() == 1
        assert result.url == "http://example.com"

    def test_add_duplicate_updates(self):
        b1 = Bookmark(url="http://example.com", title="Old")
        self.manager.add(b1)
        b2 = Bookmark(url="http://example.com", title="New")
        self.manager.add(b2)
        assert self.manager.count() == 1
        assert self.manager.get("http://example.com").title == "New"

    def test_get_bookmark(self):
        b = Bookmark(url="http://example.com")
        self.manager.add(b)
        result = self.manager.get("http://example.com")
        assert result is not None
        assert result.url == "http://example.com"

    def test_get_missing(self):
        assert self.manager.get("http://missing.com") is None

    def test_remove_bookmark(self):
        self.manager.add(Bookmark(url="http://example.com"))
        assert self.manager.remove("http://example.com") is True
        assert self.manager.count() == 0

    def test_remove_missing(self):
        assert self.manager.remove("http://missing.com") is False

    def test_list_all(self):
        self.manager.add(Bookmark(url="http://a.com"))
        self.manager.add(Bookmark(url="http://b.com"))
        assert len(self.manager.list_all()) == 2

    def test_list_by_category(self):
        self.manager.add(Bookmark(url="http://a.com", category="tech"))
        self.manager.add(Bookmark(url="http://b.com", category="news"))
        assert len(self.manager.list_by_category("tech")) == 1
        assert len(self.manager.list_by_category("news")) == 1
        assert len(self.manager.list_by_category("other")) == 0

    def test_list_by_tag(self):
        self.manager.add(Bookmark(url="http://a.com", tags=["python"]))
        self.manager.add(Bookmark(url="http://b.com", tags=["python", "web"]))
        self.manager.add(Bookmark(url="http://c.com", tags=["web"]))
        assert len(self.manager.list_by_tag("python")) == 2
        assert len(self.manager.list_by_tag("web")) == 2
        assert len(self.manager.list_by_tag("rust")) == 0

    def test_list_favorites(self):
        self.manager.add(Bookmark(url="http://a.com", is_favorite=True))
        self.manager.add(Bookmark(url="http://b.com", is_favorite=False))
        assert len(self.manager.list_favorites()) == 1

    def test_toggle_favorite(self):
        self.manager.add(Bookmark(url="http://a.com"))
        result = self.manager.toggle_favorite("http://a.com")
        assert result is not None
        assert result.is_favorite is True
        self.manager.toggle_favorite("http://a.com")
        assert self.manager.get("http://a.com").is_favorite is False

    def test_toggle_favorite_missing(self):
        result = self.manager.toggle_favorite("http://missing.com")
        assert result is None

    def test_search_by_title(self):
        self.manager.add(Bookmark(url="http://a.com", title="Python Tips"))
        self.manager.add(Bookmark(url="http://b.com", title="Rust Guide"))
        results = self.manager.search("Python")
        assert len(results) == 1
        assert results[0].title == "Python Tips"

    def test_search_by_url(self):
        self.manager.add(Bookmark(url="http://example.com/page"))
        results = self.manager.search("example")
        assert len(results) == 1

    def test_search_case_insensitive(self):
        self.manager.add(Bookmark(url="http://a.com", title="Hello World"))
        results = self.manager.search("hello")
        assert len(results) == 1

    def test_get_categories(self):
        self.manager.add(Bookmark(url="http://a.com", category="tech"))
        self.manager.add(Bookmark(url="http://b.com", category="news"))
        self.manager.add(Bookmark(url="http://c.com", category="tech"))
        categories = self.manager.get_categories()
        assert categories == ["news", "tech"]

    def test_get_all_tags(self):
        self.manager.add(Bookmark(url="http://a.com", tags=["python", "web"]))
        self.manager.add(Bookmark(url="http://b.com", tags=["rust"]))
        tags = self.manager.get_all_tags()
        assert tags == ["python", "rust", "web"]

    def test_count(self):
        assert self.manager.count() == 0
        self.manager.add(Bookmark(url="http://a.com"))
        assert self.manager.count() == 1

    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "bookmarks.json")
        self.manager.add(Bookmark(url="http://a.com", title="A", category="tech"))
        self.manager.add(Bookmark(url="http://b.com", title="B", tags=["x"]))
        self.manager.save(path)
        assert os.path.exists(path)

        manager2 = BookmarkManager()
        loaded = manager2.load(path)
        assert loaded == 2
        assert manager2.get("http://a.com").title == "A"
        assert manager2.get("http://b.com").tags == ["x"]

    def test_load_nonexistent(self):
        manager = BookmarkManager()
        loaded = manager.load("/tmp/nonexistent_bookmarks.json")
        assert loaded == 0

    def test_save_no_path(self):
        with pytest.raises(ValueError):
            self.manager.save()

    def test_load_no_path(self):
        with pytest.raises(ValueError):
            self.manager.load()
