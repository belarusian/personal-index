"""Tests for bookmark management module."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

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

    def test_get_contract_pinned(self):
        # Pin the exact contract of BookmarkManager.get.
        # Normal case: returns the SAME Bookmark object (identity, not copy).
        b = Bookmark(url="http://a.com", title="Test")
        self.manager.add(b)
        result = self.manager.get("http://a.com")
        assert result is b
        # Guard input: missing url returns None, no raise, no mutation.
        count_before = self.manager.count()
        assert self.manager.get("http://missing.com") is None
        assert self.manager.count() == count_before
        assert self.manager.get("http://a.com") is b
        assert b.title == "Test"

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

    def test_list_by_category_contract_pinned(self):
        """Pin the exact contract of BookmarkManager.list_by_category."""
        manager = BookmarkManager()
        # Guard: empty store returns empty list
        result = manager.list_by_category("tech")
        assert result == []
        assert isinstance(result, list)

        # Normal case: two bookmarks in "tech", one in "news"
        b1 = Bookmark(url="http://a.com", title="A", category="tech")
        b2 = Bookmark(url="http://b.com", title="B", category="tech")
        b3 = Bookmark(url="http://c.com", title="C", category="news")
        manager.add(b1)
        manager.add(b2)
        manager.add(b3)

        result = manager.list_by_category("tech")
        assert len(result) == 2
        # Returns the SAME objects (not copies)
        assert b1 in result
        assert b2 in result
        assert b3 not in result
        # EXACT match only: no substring / case-insensitive leakage
        assert manager.list_by_category("te") == []
        assert manager.list_by_category("TECH") == []
        # The returned list is a fresh list, not a reference to internal state
        result.append(Bookmark(url="http://d.com", category="tech"))
        assert manager.count() == 3  # internal state unaffected

    def test_list_by_tag(self):
        self.manager.add(Bookmark(url="http://a.com", tags=["python"]))
        self.manager.add(Bookmark(url="http://b.com", tags=["python", "web"]))
        self.manager.add(Bookmark(url="http://c.com", tags=["web"]))
        assert len(self.manager.list_by_tag("python")) == 2
        assert len(self.manager.list_by_tag("web")) == 2
        assert len(self.manager.list_by_tag("rust")) == 0

    def test_list_by_tag_contract_pinned(self):
        """Pin the exact contract of BookmarkManager.list_by_tag."""
        manager = BookmarkManager()
        # Guard: empty store returns empty list
        result = manager.list_by_tag("python")
        assert result == []
        assert isinstance(result, list)

        # Normal case: two bookmarks carry "python", one carries only "web"
        b1 = Bookmark(url="http://a.com", title="A", tags=["python"])
        b2 = Bookmark(url="http://b.com", title="B", tags=["python", "web"])
        b3 = Bookmark(url="http://c.com", title="C", tags=["web"])
        manager.add(b1)
        manager.add(b2)
        manager.add(b3)

        result = manager.list_by_tag("python")
        assert len(result) == 2
        # Returns the SAME objects (not copies)
        assert b1 in result
        assert b2 in result
        assert b3 not in result
        # EXACT list-membership match only: no substring / case-insensitive leakage
        assert manager.list_by_tag("py") == []
        assert manager.list_by_tag("PYTHON") == []
        # The returned list is a fresh list, not a reference to internal state
        result.append(Bookmark(url="http://d.com", tags=["python"]))
        assert manager.count() == 3  # internal state unaffected

    def test_list_favorites(self):
        self.manager.add(Bookmark(url="http://a.com", is_favorite=True))
        self.manager.add(Bookmark(url="http://b.com", is_favorite=False))
        assert len(self.manager.list_favorites()) == 1

    def test_list_favorites_contract_pinned(self):
        """Pin the exact contract of BookmarkManager.list_favorites."""
        manager = BookmarkManager()
        # Guard: empty store returns empty list
        result = manager.list_favorites()
        assert result == []
        assert isinstance(result, list)

        # Normal case: two favorites + one non-favorite
        b1 = Bookmark(url="http://a.com", title="A", is_favorite=True)
        b2 = Bookmark(url="http://b.com", title="B", is_favorite=True)
        b3 = Bookmark(url="http://c.com", title="C", is_favorite=False)
        manager.add(b1)
        manager.add(b2)
        manager.add(b3)

        result = manager.list_favorites()
        assert len(result) == 2
        # Returns the SAME objects (not copies), in insertion order
        assert result[0] is b1
        assert result[1] is b2
        assert b3 not in result
        # The returned list is a fresh list, not a reference to internal state
        result.append(Bookmark(url="http://d.com", is_favorite=True))
        assert manager.count() == 3  # internal state unaffected

        # Guard: all-non-favorite store returns empty list
        manager2 = BookmarkManager()
        manager2.add(Bookmark(url="http://e.com", is_favorite=False))
        manager2.add(Bookmark(url="http://f.com", is_favorite=False))
        assert manager2.list_favorites() == []

    def test_list_all_contract_pinned(self):
        """Pin the exact contract of BookmarkManager.list_all."""
        manager = BookmarkManager()
        # Guard: empty store returns empty list
        result = manager.list_all()
        assert result == []
        assert isinstance(result, list)

        # Normal case: add two bookmarks
        b1 = Bookmark(url="http://a.com", title="A")
        b2 = Bookmark(url="http://b.com", title="B")
        manager.add(b1)
        manager.add(b2)

        result = manager.list_all()
        assert len(result) == 2
        # Returns the SAME objects (not copies)
        assert b1 in result
        assert b2 in result
        # The returned list is a fresh list, not a reference to internal state
        result.append(Bookmark(url="http://c.com"))
        assert manager.count() == 2  # internal state unaffected

    def test_search_contract_pinned(self):
        """Pin the exact contract of BookmarkManager.search."""
        manager = BookmarkManager()
        # Guard: empty store returns empty list
        result = manager.search("anything")
        assert result == []
        assert isinstance(result, list)

        # Normal case: seed bookmarks with distinct title/description/url
        b1 = Bookmark(url="http://alpha.com/x", title="Alpha Title", description="first desc")
        b2 = Bookmark(url="http://beta.com/y", title="Beta Title", description="second desc")
        b3 = Bookmark(url="http://gamma.com/z", title="Gamma Title", description="third desc")
        manager.add(b1)
        manager.add(b2)
        manager.add(b3)

        # Match by title
        r = manager.search("alpha")
        assert r == [b1]
        assert r[0] is b1  # same object, not a copy
        # Match by description
        r = manager.search("second")
        assert r == [b2]
        assert r[0] is b2
        # Match by url
        r = manager.search("gamma.com")
        assert r == [b3]
        assert r[0] is b3

        # Case-insensitivity: uppercase query matches lowercase field
        r = manager.search("ALPHA")
        assert r == [b1]
        assert r[0] is b1

        # Multiple matches preserve insertion order
        b4 = Bookmark(url="http://delta.com/w", title="Delta Title", description="fourth desc")
        manager.add(b4)
        r = manager.search("title")
        assert r == [b1, b2, b3, b4]
        assert r[0] is b1 and r[1] is b2 and r[2] is b3 and r[3] is b4

        # Fresh-list guard: result is a new list, not internal state
        r = manager.search("title")
        r.append(Bookmark(url="http://epsilon.com"))
        assert manager.count() == 4  # internal state unaffected

        # Guard: no-match query returns empty list
        assert manager.search("zzz-no-match-zzz") == []

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

    def test_toggle_favorite_contract_pinned(self):
        # Normal case: toggle returns the mutated Bookmark, flips is_favorite,
        # and sets updated_at to a UTC ISO-8601 timestamp.
        b = Bookmark(url="http://a.com")
        self.manager.add(b)
        result = self.manager.toggle_favorite("http://a.com")
        assert result is b
        assert result.is_favorite is True
        parsed = datetime.fromisoformat(result.updated_at)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(0)
        # Guard input: missing url returns None and mutates nothing.
        count_before = self.manager.count()
        missing = self.manager.toggle_favorite("http://missing.com")
        assert missing is None
        assert self.manager.count() == count_before

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

    def test_get_categories_contract_pinned(self):
        """Pin the exact contract of BookmarkManager.get_categories."""
        manager = BookmarkManager()
        # Guard: empty store returns an empty list
        result = manager.get_categories()
        assert result == []
        assert isinstance(result, list)

        # Normal case: dedup + ascending lexicographic order
        manager.add(Bookmark(url="http://a.com", category="tech"))
        manager.add(Bookmark(url="http://b.com", category="news"))
        manager.add(Bookmark(url="http://c.com", category="tech"))
        manager.add(Bookmark(url="http://d.com", category="art"))
        result = manager.get_categories()
        assert result == ["art", "news", "tech"]
        # element type is str
        assert all(isinstance(c, str) for c in result)
        # FRESH list: mutating the result does not touch internal state
        result.append("injected")
        assert manager.get_categories() == ["art", "news", "tech"]
        # Read-only: the call itself does not mutate the store
        assert manager.count() == 4

    def test_get_all_tags(self):
        self.manager.add(Bookmark(url="http://a.com", tags=["python", "web"]))
        self.manager.add(Bookmark(url="http://b.com", tags=["rust"]))
        tags = self.manager.get_all_tags()
        assert tags == ["python", "rust", "web"]

    def test_get_all_tags_contract_pinned(self):
        """Pin the exact contract of BookmarkManager.get_all_tags."""
        manager = BookmarkManager()
        # Guard: empty store returns an empty list
        result = manager.get_all_tags()
        assert result == []
        assert isinstance(result, list)

        # Normal case: dedup + ascending lexicographic order
        manager.add(Bookmark(url="http://a.com", tags=["python", "web"]))
        manager.add(Bookmark(url="http://b.com", tags=["rust", "python"]))
        manager.add(Bookmark(url="http://c.com", tags=["art"]))
        result = manager.get_all_tags()
        assert result == ["art", "python", "rust", "web"]
        # element type is str
        assert all(isinstance(t, str) for t in result)
        # FRESH list: mutating the result does not touch internal state
        result.append("injected")
        assert manager.get_all_tags() == ["art", "python", "rust", "web"]
        # Read-only: the call itself does not mutate the store
        assert manager.count() == 3

    def test_count(self):
        assert self.manager.count() == 0
        self.manager.add(Bookmark(url="http://a.com"))
        assert self.manager.count() == 1

    def test_count_contract_pinned(self):
        """Pin the exact contract of BookmarkManager.count."""
        manager = BookmarkManager()
        # Guard: empty store returns 0
        result = manager.count()
        assert result == 0
        assert isinstance(result, int)
        # Normal case: counts the TOTAL number of stored bookmarks
        manager.add(Bookmark(url="http://a.com"))
        manager.add(Bookmark(url="http://b.com"))
        manager.add(Bookmark(url="http://c.com"))
        assert manager.count() == 3
        # Read-only: the call itself does not mutate the store
        before = manager.list_all()
        manager.count()
        assert manager.list_all() == before
        assert manager.count() == 3
        # Docstring pins the exact contract (stable fragment, lowercased)
        doc = manager.count.__doc__.lower()
        assert "not mutate the internal state" in doc
        assert "returns 0" in doc


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

    def test_load_null_json(self, tmp_path):
        path = str(tmp_path / "bookmarks.json")
        with open(path, "w") as f:
            f.write("null")
        manager = BookmarkManager()
        loaded = manager.load(path)
        assert loaded == 0
        assert manager.count() == 0

    def test_load_dict_json(self, tmp_path):
        path = str(tmp_path / "bookmarks.json")
        with open(path, "w") as f:
            json.dump({"key": "val"}, f)
        manager = BookmarkManager()
        loaded = manager.load(path)
        assert loaded == 0
        assert manager.count() == 0

    def test_load_number_json(self, tmp_path):
        path = str(tmp_path / "bookmarks.json")
        with open(path, "w") as f:
            f.write("42")
        manager = BookmarkManager()
        loaded = manager.load(path)
        assert loaded == 0
        assert manager.count() == 0

    def test_load_corrupt_json(self, tmp_path):
        path = str(tmp_path / "bookmarks.json")
        with open(path, "w") as f:
            f.write("{")
        manager = BookmarkManager()
        loaded = manager.load(path)
        assert loaded == 0
        assert manager.count() == 0

    def test_load_truncated_json(self, tmp_path):
        path = str(tmp_path / "bookmarks.json")
        with open(path, "w") as f:
            f.write('[{"url": "http://exa')
        manager = BookmarkManager()
        loaded = manager.load(path)
        assert loaded == 0
        assert manager.count() == 0

    def test_load_replaces_set_and_guard_preserves(self, tmp_path):
        # Normal path: a valid top-level list replaces the current set and
        # returns the number loaded.
        manager = BookmarkManager()
        manager.add(Bookmark(url="http://old.com", title="Old"))
        path = str(tmp_path / "bookmarks.json")
        with open(path, "w") as f:
            json.dump(
                [
                    {"url": "http://a.com", "title": "A"},
                    {"url": "http://b.com", "title": "B"},
                ],
                f,
            )
        loaded = manager.load(path)
        assert loaded == 2
        assert manager.count() == 2
        assert manager.get("http://old.com") is None
        assert manager.get("http://a.com").title == "A"
        assert manager.get("http://b.com").title == "B"

        # Guard path: a non-list top-level value returns 0 and leaves the
        # existing set untouched (no clear, no replacement).
        with open(path, "w") as f:
            json.dump({"key": "val"}, f)
        loaded = manager.load(path)
        assert loaded == 0
        assert manager.count() == 2
        assert manager.get("http://a.com").title == "A"
        assert manager.get("http://b.com").title == "B"

    def test_load_default_replaces_unsaved(self, tmp_path):
        # Normal path: default (merge=False) replaces the in-memory set with
        # the file contents and returns the file count, dropping any unsaved
        # in-memory bookmark.
        manager = BookmarkManager()
        manager.add(Bookmark(url="http://unsaved.com", title="Unsaved"))
        path = str(tmp_path / "bookmarks.json")
        with open(path, "w") as f:
            json.dump(
                [
                    {"url": "http://a.com", "title": "A"},
                    {"url": "http://b.com", "title": "B"},
                ],
                f,
            )
        loaded = manager.load(path)
        assert loaded == 2
        assert manager.get("http://unsaved.com") is None
        assert manager.get("http://a.com").title == "A"
        assert manager.get("http://b.com").title == "B"
        assert manager.count() == 2

    def test_load_merge_preserves_and_upserts(self, tmp_path):
        # merge=True upserts file bookmarks over the current set: a URL
        # collision preserves the existing created_at and refreshes
        # updated_at, file-only and memory-only bookmarks are both kept, and
        # the return value is the number of bookmarks read from the file.
        manager = BookmarkManager()
        known_created = "2020-01-01T00:00:00+00:00"
        manager.add(
            Bookmark(url="http://a.com", title="A-old", created_at=known_created)
        )
        manager.add(Bookmark(url="http://mem_only.com", title="MemOnly"))
        path = str(tmp_path / "bookmarks.json")
        with open(path, "w") as f:
            json.dump(
                [
                    {"url": "http://a.com", "title": "A-new"},
                    {"url": "http://file_only.com", "title": "FileOnly"},
                ],
                f,
            )
        loaded = manager.load(path, merge=True)
        assert loaded == 2
        a = manager.get("http://a.com")
        assert a is not None
        assert a.created_at == known_created
        assert a.title == "A-new"
        assert manager.get("http://mem_only.com") is not None
        assert manager.get("http://file_only.com") is not None
        assert manager.count() == 3

    def test_load_merge_missing_file_noop(self, tmp_path):
        # Guard path: merge=True with a missing file returns 0 and leaves the
        # in-memory set untouched (no clear, no upsert).
        manager = BookmarkManager()
        manager.add(Bookmark(url="http://keep.com", title="Keep"))
        loaded = manager.load(str(tmp_path / "nope.json"), merge=True)
        assert loaded == 0
        assert manager.count() == 1
        assert manager.get("http://keep.com").title == "Keep"
