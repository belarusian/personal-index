"""Adversarial deep tests for personal_index.tags (TagStore / Tag).

Never-probed subsystem (cycle 153). Attacks the documented contracts with
guard inputs (None/empty/whitespace/unicode/duplicate/out-of-range),
round-trips, idempotence, property checks, and one end-to-end run through
the installed CLI (`personal-index tags add/list/remove`).

Documented contracts pinned here (from personal_index/tags.py docstrings):
  - add_tag_to_page auto-creates the tag if missing and always returns True.
  - remove_tag_from_page returns True ONLY if the tag was present and removed;
    False (no-op) otherwise.
  - delete_tag removes the tag and strips it from every page; returns bool.
  - get_tags_for_page drops dangling names (recorded on a page but no longer
    registered in the tag registry).
  - get_pages_for_tag returns [] when the tag is not registered.
  - _load tolerates corrupt / non-dict JSON by resetting to an empty store.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from personal_index.tags import Tag, TagStore


# ── Tag dataclass semantics ────────────────────────────────────────────
class TestTagDataclass:
    def test_eq_by_name_ignores_color(self):
        a = Tag(name="x", color="#111111")
        b = Tag(name="x", color="#222222")
        assert a == b
        assert hash(a) == hash(b)

    def test_neq_different_name(self):
        assert Tag(name="a") != Tag(name="b")

    def test_lt_orders_by_name(self):
        assert Tag(name="apple") < Tag(name="banana")
        assert not (Tag(name="banana") < Tag(name="apple"))

    def test_lt_non_tag_returns_notimplemented(self):
        assert Tag(name="a").__lt__("string") is NotImplemented

    def test_default_fields(self):
        t = Tag(name="n")
        assert t.color == "#3498db"
        assert t.description == ""
        assert t.created_at  # non-empty ISO timestamp


# ── Guard inputs ───────────────────────────────────────────────────────
class TestGuardInputs:
    def test_empty_tag_name_is_stored(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.add_tag_to_page("https://x.com", "") is True
        assert store.get_tag_count() == 1
        assert store.get_tag("") is not None

    def test_whitespace_tag_name_is_stored(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.add_tag_to_page("https://x.com", "   ") is True
        assert store.get_tag("   ") is not None

    def test_unicode_tag_name_roundtrip(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        store.add_tag_to_page("https://x.com", "тэг-日本語-🏷️")
        assert store.get_tag("тэг-日本語-🏷️") is not None
        assert "тэг-日本語-🏷️" in {t.name for t in store.get_tags_for_page("https://x.com")}

    def test_empty_url_is_stored(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.add_tag_to_page("", "tag") is True
        assert "" in store.get_pages_for_tag("tag")

    def test_get_tag_missing_returns_none(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.get_tag("nope") is None

    def test_get_tags_for_page_unknown_url_empty(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.get_tags_for_page("https://unknown.com") == []

    def test_get_pages_for_tag_unregistered_empty(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.get_pages_for_tag("ghost") == []


# ── Idempotence ────────────────────────────────────────────────────────
class TestIdempotence:
    def test_add_same_tag_twice_no_dup(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        store.add_tag_to_page("https://x.com", "t")
        store.add_tag_to_page("https://x.com", "t")
        assert store.get_tag_count() == 1
        assert store.get_pages_for_tag("t") == ["https://x.com"]

    def test_remove_absent_tag_is_noop_false(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.remove_tag_from_page("https://x.com", "t") is False

    def test_remove_present_then_absent(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        store.add_tag_to_page("https://x.com", "t")
        assert store.remove_tag_from_page("https://x.com", "t") is True
        assert store.remove_tag_from_page("https://x.com", "t") is False

    def test_delete_missing_tag_false(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.delete_tag("ghost") is False

    def test_remove_page_unknown_false(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        assert store.remove_page("https://unknown.com") is False


# ── Property checks ────────────────────────────────────────────────────
class TestProperties:
    def test_delete_tag_strips_from_all_pages(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        for url in ("https://a.com", "https://b.com", "https://c.com"):
            store.add_tag_to_page(url, "shared")
        assert store.delete_tag("shared") is True
        assert store.get_tag_count() == 0
        for url in ("https://a.com", "https://b.com", "https://c.com"):
            assert store.get_tags_for_page(url) == []

    def test_dangling_name_dropped_from_page(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        store.add_tag_to_page("https://x.com", "keep")
        store.add_tag_to_page("https://x.com", "drop")
        store.delete_tag("drop")
        names = {t.name for t in store.get_tags_for_page("https://x.com")}
        assert names == {"keep"}

    def test_tagged_page_count_ignores_empty(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        store.add_tag_to_page("https://a.com", "t")
        store.add_tag_to_page("https://a.com", "t2")
        store.add_tag_to_page("https://b.com", "t")
        # a page with all tags removed should not count
        store.remove_tag_from_page("https://b.com", "t")
        assert store.get_tagged_page_count() == 1

    def test_multiple_tags_per_page(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        for t in ("a", "b", "c"):
            store.add_tag_to_page("https://x.com", t)
        assert {t.name for t in store.get_tags_for_page("https://x.com")} == {"a", "b", "c"}
        assert store.get_tag_count() == 3

    def test_create_tag_replaces_preserves_pages(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "t.json"))
        store.add_tag_to_page("https://x.com", "t")
        store.create_tag("t", color="#ff0000", description="new")
        assert store.get_tag("t").color == "#ff0000"
        assert store.get_tag("t").description == "new"
        assert store.get_pages_for_tag("t") == ["https://x.com"]


# ── Persistence round-trips ────────────────────────────────────────────
class TestPersistence:
    def test_roundtrip_preserves_tags_and_pages(self, tmp_path):
        path = str(tmp_path / "t.json")
        store = TagStore(store_path=path)
        store.add_tag_to_page("https://a.com", "t1")
        store.add_tag_to_page("https://b.com", "t1")
        store.add_tag_to_page("https://a.com", "t2")
        store.create_tag("t1", color="#00ff00", description="d")

        reloaded = TagStore(store_path=path)
        assert reloaded.get_tag_count() == 2
        assert reloaded.get_tag("t1").color == "#00ff00"
        assert reloaded.get_tag("t1").description == "d"
        assert set(reloaded.get_pages_for_tag("t1")) == {"https://a.com", "https://b.com"}
        assert reloaded.get_pages_for_tag("t2") == ["https://a.com"]
        assert {t.name for t in reloaded.get_tags_for_page("https://a.com")} == {"t1", "t2"}

    def test_roundtrip_unicode(self, tmp_path):
        path = str(tmp_path / "t.json")
        store = TagStore(store_path=path)
        store.add_tag_to_page("https://x.com", "日本語")
        reloaded = TagStore(store_path=path)
        assert reloaded.get_tag("日本語") is not None
        assert reloaded.get_pages_for_tag("日本語") == ["https://x.com"]

    def test_corrupt_json_resets_to_empty(self, tmp_path):
        path = str(tmp_path / "t.json")
        with open(path, "w") as f:
            f.write("{ this is not valid json ]]]")
        store = TagStore(store_path=path)
        assert store.get_tag_count() == 0
        assert store.list_tags() == []

    def test_non_dict_json_resets_to_empty(self, tmp_path):
        path = str(tmp_path / "t.json")
        with open(path, "w") as f:
            json.dump(["a", "b", "c"], f)
        store = TagStore(store_path=path)
        assert store.get_tag_count() == 0

    def test_no_store_path_in_memory_only(self):
        store = TagStore(store_path=None)
        store.add_tag_to_page("https://x.com", "t")
        assert store.get_tag_count() == 1
        # a second in-memory store must not see it
        other = TagStore(store_path=None)
        assert other.get_tag_count() == 0

    def test_clear_resets_and_persists(self, tmp_path):
        path = str(tmp_path / "t.json")
        store = TagStore(store_path=path)
        store.add_tag_to_page("https://x.com", "t")
        store.clear()
        assert store.get_tag_count() == 0
        reloaded = TagStore(store_path=path)
        assert reloaded.get_tag_count() == 0


# ── End-to-end CLI ─────────────────────────────────────────────────────
class TestEndToEndCLI:
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "personal_index.cli", *args],
            capture_output=True,
            text=True,
        )

    def test_tags_add_list_remove_roundtrip(self, tmp_path):
        dd = str(tmp_path / "data")
        url = "https://example.com/page1"

        r = self._run("tags", "add", "important", url, "--data-dir", dd)
        assert r.returncode == 0, r.stderr
        assert f"Added tag 'important' to {url}" in r.stdout

        r = self._run("tags", "list", "--data-dir", dd)
        assert r.returncode == 0, r.stderr
        assert "important (1 pages)" in r.stdout

        # idempotent re-add: still one page
        r = self._run("tags", "add", "important", url, "--data-dir", dd)
        assert r.returncode == 0, r.stderr
        r = self._run("tags", "list", "--data-dir", dd)
        assert "important (1 pages)" in r.stdout

        r = self._run("tags", "remove", "important", url, "--data-dir", dd)
        assert r.returncode == 0, r.stderr
        assert f"Removed tag 'important' from {url}" in r.stdout

        # removing again is a no-op
        r = self._run("tags", "remove", "important", url, "--data-dir", dd)
        assert r.returncode == 0, r.stderr
        assert f"Tag 'important' not found on {url}" in r.stdout

    def test_tags_list_empty(self, tmp_path):
        dd = str(tmp_path / "data")
        r = self._run("tags", "list", "--data-dir", dd)
        assert r.returncode == 0, r.stderr
        assert "No tags configured." in r.stdout

    def test_tags_add_unicode(self, tmp_path):
        dd = str(tmp_path / "data")
        url = "https://example.com/日本語"
        r = self._run("tags", "add", "тэг", url, "--data-dir", dd)
        assert r.returncode == 0, r.stderr
        r = self._run("tags", "list", "--data-dir", dd)
        assert r.returncode == 0, r.stderr
        assert "тэг (1 pages)" in r.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
