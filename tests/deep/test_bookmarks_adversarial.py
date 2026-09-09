"""Adversarial deep tests for personal_index/bookmarks.py (cycle 184).

Bookmarks is a clean module: every probed behavior matches the exact contract
in docs/bookmarks.md. The documented "Contract Holes" (load silent full
replacement / ARCH-39; from_dict KeyError mid-loop after clear; save not
creating parent dirs; add collision clobbering tags/favorite) are documented
design constraints, NOT new defects, so they are pinned here as armor of the
CURRENT documented behavior rather than filed as QA tickets.

Coverage: Bookmark dataclass (post_init timestamps, to_dict/from_dict
round-trip, missing-url KeyError), BookmarkManager (add upsert + collision
semantics, get/remove, list_* ordering + filters, toggle_favorite, search
case-insensitivity, get_categories/get_all_tags sorting, count), save/load
(defensive loads: missing file / malformed JSON / non-list top-level / empty
list / no-path ValueError; round-trip; duplicate-URL last-wins; unicode).
"""

from __future__ import annotations

import json
import os

import pytest

from personal_index.bookmarks import Bookmark, BookmarkManager


# ---------------------------------------------------------------------------
# Bookmark dataclass
# ---------------------------------------------------------------------------
class TestBookmarkDataclass:
    def test_post_init_fills_timestamps_when_empty(self):
        b = Bookmark(url="http://a.com")
        assert b.created_at != ""
        assert b.updated_at == b.created_at

    def test_post_init_keeps_explicit_timestamps(self):
        b = Bookmark(
            url="http://a.com",
            created_at="2020-01-01T00:00:00+00:00",
            updated_at="2020-02-02T00:00:00+00:00",
        )
        assert b.created_at == "2020-01-01T00:00:00+00:00"
        assert b.updated_at == "2020-02-02T00:00:00+00:00"

    def test_post_init_updated_defaults_to_created(self):
        b = Bookmark(url="http://a.com", created_at="2021-03-03T00:00:00+00:00")
        assert b.updated_at == "2021-03-03T00:00:00+00:00"

    def test_to_dict_has_all_eight_fields(self):
        b = Bookmark(url="http://a.com", title="T", description="D",
                     category="c", tags=["x"], is_favorite=True)
        d = b.to_dict()
        assert set(d.keys()) == {
            "url", "title", "description", "category", "tags",
            "created_at", "updated_at", "is_favorite",
        }

    def test_to_dict_from_dict_round_trip(self):
        b = Bookmark(url="http://ünïcode.com/путь", title="Тест",
                     description="d", category="cat", tags=["a", "b"],
                     created_at="2021-05-05T00:00:00+00:00", is_favorite=True)
        b2 = Bookmark.from_dict(b.to_dict())
        assert b2.url == b.url
        assert b2.title == b.title
        assert b2.tags == b.tags
        assert b2.is_favorite is True
        assert b2.created_at == b.created_at

    def test_from_dict_missing_url_raises_keyerror(self):
        # Documented: url read with data["url"] -> KeyError.
        with pytest.raises(KeyError):
            Bookmark.from_dict({"title": "no-url"})

    def test_from_dict_defaults_for_missing_optional_fields(self):
        b = Bookmark.from_dict({"url": "http://a.com"})
        assert b.title == ""
        assert b.description == ""
        assert b.category == "uncategorized"
        assert b.tags == []
        assert b.is_favorite is False


# ---------------------------------------------------------------------------
# BookmarkManager: add / get / remove
# ---------------------------------------------------------------------------
class TestAddGetRemove:
    def test_add_returns_stored_object(self):
        m = BookmarkManager()
        b = Bookmark(url="http://a.com")
        ret = m.add(b)
        assert ret is b
        assert ret.updated_at != ""

    def test_get_existing_and_missing(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com"))
        assert m.get("http://a.com") is not None
        assert m.get("http://nope.com") is None

    def test_remove_returns_bool(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com"))
        assert m.remove("http://a.com") is True
        assert m.remove("http://a.com") is False

    def test_add_collision_preserves_created_at_clobbers_rest(self):
        # Documented asymmetry: created_at preserved, others clobbered.
        m = BookmarkManager()
        m.add(Bookmark(url="http://c.com", title="T1", tags=["x"],
                       is_favorite=True,
                       created_at="2020-01-01T00:00:00+00:00"))
        m.add(Bookmark(url="http://c.com", title="T2"))
        got = m.get("http://c.com")
        assert got.created_at == "2020-01-01T00:00:00+00:00"
        assert got.title == "T2"
        assert got.tags == []
        assert got.is_favorite is False

    def test_add_distinct_urls_count(self):
        m = BookmarkManager()
        for u in ["http://a.com", "http://b.com", "http://c.com"]:
            m.add(Bookmark(url=u))
        assert m.count() == 3


# ---------------------------------------------------------------------------
# list_* ordering + filters
# ---------------------------------------------------------------------------
class TestListFilters:
    def test_list_all_insertion_order(self):
        m = BookmarkManager()
        for u in ["http://z.com", "http://a.com", "http://m.com"]:
            m.add(Bookmark(url=u))
        assert [b.url for b in m.list_all()] == [
            "http://z.com", "http://a.com", "http://m.com",
        ]

    def test_list_by_category_exact_match(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com", category="alpha"))
        m.add(Bookmark(url="http://b.com", category="beta"))
        m.add(Bookmark(url="http://c.com", category="alpha"))
        urls = [b.url for b in m.list_by_category("alpha")]
        assert urls == ["http://a.com", "http://c.com"]

    def test_list_by_tag_membership(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com", tags=["x", "y"]))
        m.add(Bookmark(url="http://b.com", tags=["y"]))
        m.add(Bookmark(url="http://c.com", tags=["z"]))
        assert [b.url for b in m.list_by_tag("y")] == ["http://a.com", "http://b.com"]

    def test_list_favorites(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com", is_favorite=True))
        m.add(Bookmark(url="http://b.com", is_favorite=False))
        assert [b.url for b in m.list_favorites()] == ["http://a.com"]

    def test_toggle_favorite_flips_and_refreshes(self):
        m = BookmarkManager()
        b = Bookmark(url="http://a.com", is_favorite=False)
        m.add(b)
        before = b.updated_at
        ret = m.toggle_favorite("http://a.com")
        assert ret is b
        assert b.is_favorite is True
        assert b.updated_at != before
        m.toggle_favorite("http://a.com")
        assert b.is_favorite is False

    def test_toggle_favorite_unknown_returns_none(self):
        m = BookmarkManager()
        assert m.toggle_favorite("http://nope.com") is None


# ---------------------------------------------------------------------------
# search / categories / tags
# ---------------------------------------------------------------------------
class TestSearchAndAggregates:
    def test_search_case_insensitive_across_fields(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://Example.com", title="Python Guide"))
        m.add(Bookmark(url="http://x.com", description="python tutorial"))
        m.add(Bookmark(url="http://y.com", title="Java"))
        urls = [b.url for b in m.search("PY")]
        assert urls == ["http://Example.com", "http://x.com"]

    def test_search_no_match_returns_empty(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com", title="Alpha"))
        assert m.search("zzz") == []

    def test_get_categories_sorted_unique(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com", category="zeta"))
        m.add(Bookmark(url="http://b.com", category="alpha"))
        m.add(Bookmark(url="http://c.com", category="zeta"))
        assert m.get_categories() == ["alpha", "zeta"]

    def test_get_all_tags_sorted_unique(self):
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com", tags=["z", "a"]))
        m.add(Bookmark(url="http://b.com", tags=["a", "m"]))
        assert m.get_all_tags() == ["a", "m", "z"]

    def test_empty_manager_aggregates(self):
        m = BookmarkManager()
        assert m.get_categories() == []
        assert m.get_all_tags() == []
        assert m.count() == 0
        assert m.list_all() == []


# ---------------------------------------------------------------------------
# save / load defensive + round-trip
# ---------------------------------------------------------------------------
class TestSaveLoad:
    def test_save_no_path_raises_valueerror(self):
        m = BookmarkManager()
        with pytest.raises(ValueError):
            m.save()

    def test_load_no_path_raises_valueerror(self):
        m = BookmarkManager()
        with pytest.raises(ValueError):
            m.load()

    def test_load_missing_file_returns_zero_untouched(self, tmp_path):
        m = BookmarkManager()
        m.add(Bookmark(url="http://keep.com"))
        assert m.load(str(tmp_path / "nope.json")) == 0
        assert m.count() == 1

    def test_load_malformed_json_returns_zero_untouched(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{bad json")
        m = BookmarkManager()
        m.add(Bookmark(url="http://keep.com"))
        assert m.load(str(f)) == 0
        assert m.count() == 1

    def test_load_non_list_top_level_returns_zero_untouched(self, tmp_path):
        f = tmp_path / "dict.json"
        f.write_text(json.dumps({"url": "http://x.com"}))
        m = BookmarkManager()
        m.add(Bookmark(url="http://keep.com"))
        assert m.load(str(f)) == 0
        assert m.count() == 1

    def test_load_empty_list_clears_and_returns_zero(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]")
        m = BookmarkManager()
        m.add(Bookmark(url="http://keep.com"))
        assert m.load(str(f)) == 0
        assert m.count() == 0

    def test_save_load_round_trip_unicode(self, tmp_path):
        f = tmp_path / "rt.json"
        m = BookmarkManager(storage_path=str(f))
        m.add(Bookmark(url="http://ünïcode.com/путь", title="Тест",
                       category="cat", tags=["a", "b"],
                       created_at="2021-05-05T00:00:00+00:00",
                       is_favorite=True))
        m.add(Bookmark(url="http://b.com", title="B"))
        m.save()
        m2 = BookmarkManager()
        assert m2.load(str(f)) == 2
        got = m2.get("http://ünïcode.com/путь")
        assert got is not None
        assert got.title == "Тест"
        assert got.tags == ["a", "b"]
        assert got.is_favorite is True
        assert got.created_at == "2021-05-05T00:00:00+00:00"

    def test_load_duplicate_url_last_wins_deduped(self, tmp_path):
        f = tmp_path / "dup.json"
        f.write_text(json.dumps([
            {"url": "http://d.com", "title": "first"},
            {"url": "http://d.com", "title": "second"},
        ]))
        m = BookmarkManager()
        assert m.load(str(f)) == 1
        assert m.get("http://d.com").title == "second"

    def test_load_replaces_current_set(self, tmp_path):
        # Documented hole (ARCH-39): load is a silent full replacement.
        f = tmp_path / "rep.json"
        f.write_text(json.dumps([{"url": "http://new.com"}]))
        m = BookmarkManager()
        m.add(Bookmark(url="http://old.com"))
        assert m.load(str(f)) == 1
        assert m.count() == 1
        assert m.get("http://old.com") is None
        assert m.get("http://new.com") is not None

    def test_save_returns_path_written(self, tmp_path):
        f = tmp_path / "out.json"
        m = BookmarkManager()
        m.add(Bookmark(url="http://a.com"))
        assert m.save(str(f)) == str(f)
        assert os.path.exists(str(f))

    def test_load_uses_storage_path_default(self, tmp_path):
        f = tmp_path / "sp.json"
        f.write_text(json.dumps([{"url": "http://a.com"}]))
        m = BookmarkManager(storage_path=str(f))
        assert m.load() == 1
        assert m.count() == 1
