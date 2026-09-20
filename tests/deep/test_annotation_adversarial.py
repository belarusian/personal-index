"""Adversarial deep tests for personal_index/annotation.py.

Cycle 287 — first deep-probe of the never-probed module `annotation`
(221 lines: `AnnotationType` enum, `Annotation` dataclass, `AnnotationStore`).

Covers the documented contracts:
  - AnnotationStore.add: upsert with reconciliation; postcondition "each id
    maps to exactly one URL".
  - AnnotationStore.get / get_by_url / get_by_type: lookups, None on miss.
  - AnnotationStore.update: returns bool, merges metadata, sets updated_at.
  - AnnotationStore.remove / remove_by_url: return bool / int.
  - AnnotationStore.search: case-insensitive substring over url + str value.
  - AnnotationStore.count / get_stats: totals, by_type, urls_annotated.
  - Annotation.update / to_dict: value/metadata merge, serialization.

Plus: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, error paths, and an end-to-end CLI smoke run.

QA-49: get_stats()["urls_annotated"] over-counts. It is computed as
len(self._by_url), but the add() upsert reconciliation (and remove()) leave
EMPTY index lists behind in _by_url, so a URL that no longer has any
annotation is still counted as "annotated". The docstring promises "number of
annotated URLs" — a URL with an empty index list has zero annotations and must
not be counted. Pinned xfail-strict below so main stays green while the defect
is documented for the implementer.
"""

from __future__ import annotations

import subprocess
import sys
import time

import pytest

from personal_index.annotation import Annotation, AnnotationStore, AnnotationType


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _ann(annotation_id: str, url: str, atype: AnnotationType = AnnotationType.NOTE, value=None, **kw) -> Annotation:
    return Annotation(
        annotation_id=annotation_id,
        url=url,
        annotation_type=atype,
        value=value,
        **kw,
    )


@pytest.fixture
def store() -> AnnotationStore:
    return AnnotationStore()


# ---------------------------------------------------------------------------
# add() — upsert + reconciliation
# ---------------------------------------------------------------------------


class TestAdd:
    def test_add_registers_and_indexes(self, store: AnnotationStore) -> None:
        a = _ann("a1", "http://x/1")
        store.add(a)
        assert store.get("a1") is a
        assert [x.annotation_id for x in store.get_by_url("http://x/1")] == ["a1"]
        assert store.count == 1

    def test_add_new_id_unique(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1"))
        store.add(_ann("a2", "http://x/1"))
        assert store.count == 2
        assert len(store.get_by_url("http://x/1")) == 2

    def test_upsert_same_id_same_url_no_duplicate_index(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1", value="old"))
        store.add(_ann("a1", "http://x/1", value="new"))
        # id appears exactly once in the url index
        assert store.get_by_url("http://x/1")[0].value == "new"
        assert len(store.get_by_url("http://x/1")) == 1
        assert store.count == 1

    def test_upsert_same_id_new_url_reconciles(self, store: AnnotationStore) -> None:
        """Postcondition: each id maps to exactly one URL."""
        store.add(_ann("a1", "http://x/1"))
        store.add(_ann("a1", "http://x/2"))
        # id must be reachable only via the new url
        got = store.get("a1")
        assert got is not None and got.url == "http://x/2"
        assert [x.annotation_id for x in store.get_by_url("http://x/2")] == ["a1"]
        # old url must not return the id (stale id filtered by get_by_url)
        assert store.get_by_url("http://x/1") == []

    def test_upsert_preserves_created_at(self, store: AnnotationStore) -> None:
        first = _ann("a1", "http://x/1")
        store.add(first)
        time.sleep(0.01)
        second = _ann("a1", "http://x/2", created_at=first.created_at)
        store.add(second)
        got = store.get("a1")
        assert got is not None and got.created_at == first.created_at

    def test_add_unicode_url_and_value(self, store: AnnotationStore) -> None:
        url = "http://ünïcode/🎉"
        store.add(_ann("a1", url, value="café 🚀"))
        got = store.get("a1")
        assert got is not None and got.url == url
        assert store.get_by_url(url)[0].value == "café 🚀"

    def test_add_empty_url_and_value(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "", value=""))
        got = store.get("a1")
        assert got is not None and got.url == ""
        assert store.get_by_url("") == [store.get("a1")]

    def test_add_whitespace_url(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "   \t\n"))
        assert store.get_by_url("   \t\n")[0].annotation_id == "a1"

    def test_add_oversized_value(self, store: AnnotationStore) -> None:
        big = "A" * (1024 * 1024)
        store.add(_ann("a1", "http://x/1", value=big))
        got = store.get("a1")
        assert got is not None and len(got.value) == 1024 * 1024

    def test_add_none_raises(self, store: AnnotationStore) -> None:
        """None is not an Annotation; the store must reject it (any exception)."""
        with pytest.raises(Exception):
            store.add(None)  # type: ignore[arg-type]

    def test_add_non_annotation_raises(self, store: AnnotationStore) -> None:
        """A bare string is not an Annotation; must be rejected."""
        with pytest.raises(Exception):
            store.add("not-an-annotation")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get() / get_by_url() / get_by_type()
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_miss_returns_none(self, store: AnnotationStore) -> None:
        assert store.get("nope") is None

    def test_get_empty_id_returns_none(self, store: AnnotationStore) -> None:
        assert store.get("") is None

    def test_get_none_id_returns_none(self, store: AnnotationStore) -> None:
        assert store.get(None) is None  # type: ignore[arg-type]

    def test_get_round_trip(self, store: AnnotationStore) -> None:
        a = _ann("a1", "http://x/1", value="v", author="me")
        store.add(a)
        got = store.get("a1")
        assert got is a
        assert got.value == "v"
        assert got.author == "me"

    def test_get_by_url_miss_returns_empty(self, store: AnnotationStore) -> None:
        assert store.get_by_url("http://nope") == []

    def test_get_by_url_multiple(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1"))
        store.add(_ann("a2", "http://x/1"))
        store.add(_ann("a3", "http://x/2"))
        assert {x.annotation_id for x in store.get_by_url("http://x/1")} == {"a1", "a2"}
        assert {x.annotation_id for x in store.get_by_url("http://x/2")} == {"a3"}

    def test_get_by_type(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1", AnnotationType.NOTE))
        store.add(_ann("a2", "http://x/1", AnnotationType.HIGHLIGHT))
        store.add(_ann("a3", "http://x/2", AnnotationType.NOTE))
        notes = store.get_by_type(AnnotationType.NOTE)
        assert {x.annotation_id for x in notes} == {"a1", "a3"}
        assert store.get_by_type(AnnotationType.FLAG) == []


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_update_miss_returns_false(self, store: AnnotationStore) -> None:
        assert store.update("ghost", value="x") is False

    def test_update_sets_value_and_updated_at(self, store: AnnotationStore) -> None:
        a = _ann("a1", "http://x/1", value="old")
        store.add(a)
        assert a.updated_at is None  # fresh annotation has no updated_at
        time.sleep(0.01)
        assert store.update("a1", value="new") is True
        assert a.value == "new"
        assert a.updated_at is not None  # update() stamps updated_at

    def test_update_merges_metadata(self, store: AnnotationStore) -> None:
        a = _ann("a1", "http://x/1", metadata={"k1": "v1"})
        store.add(a)
        store.update("a1", metadata={"k2": "v2"})
        assert a.metadata == {"k1": "v1", "k2": "v2"}

    def test_update_metadata_overwrites_same_key(self, store: AnnotationStore) -> None:
        a = _ann("a1", "http://x/1", metadata={"k": "old"})
        store.add(a)
        store.update("a1", metadata={"k": "new"})
        assert a.metadata["k"] == "new"

    def test_update_none_value_is_noop(self, store: AnnotationStore) -> None:
        """value=None is treated as 'not provided' (is-not-None guard)."""
        a = _ann("a1", "http://x/1", value="keep")
        store.add(a)
        store.update("a1", value=None)
        assert a.value == "keep"

    def test_update_unicode_value(self, store: AnnotationStore) -> None:
        a = _ann("a1", "http://x/1")
        store.add(a)
        store.update("a1", value="ünïcode 🎯")
        assert a.value == "ünïcode 🎯"

    def test_update_empty_value(self, store: AnnotationStore) -> None:
        a = _ann("a1", "http://x/1", value="old")
        store.add(a)
        store.update("a1", value="")
        assert a.value == ""


# ---------------------------------------------------------------------------
# remove() / remove_by_url()
# ---------------------------------------------------------------------------


class TestRemove:
    def test_remove_miss_returns_false(self, store: AnnotationStore) -> None:
        assert store.remove("ghost") is False

    def test_remove_empty_id_returns_false(self, store: AnnotationStore) -> None:
        assert store.remove("") is False

    def test_remove_returns_true_and_deletes(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1"))
        assert store.remove("a1") is True
        assert store.get("a1") is None
        assert store.count == 0

    def test_remove_idempotent(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1"))
        assert store.remove("a1") is True
        assert store.remove("a1") is False

    def test_remove_updates_url_index(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1"))
        store.add(_ann("a2", "http://x/1"))
        store.remove("a1")
        assert {x.annotation_id for x in store.get_by_url("http://x/1")} == {"a2"}

    def test_remove_by_url_returns_count(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1"))
        store.add(_ann("a2", "http://x/1"))
        store.add(_ann("a3", "http://x/2"))
        assert store.remove_by_url("http://x/1") == 2
        assert store.count == 1
        assert store.get_by_url("http://x/1") == []
        assert store.get_by_url("http://x/2") == [store.get("a3")]

    def test_remove_by_url_miss_returns_zero(self, store: AnnotationStore) -> None:
        assert store.remove_by_url("http://nope") == 0


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_by_url(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://example.com/page"))
        store.add(_ann("a2", "http://other.com/page"))
        assert {x.annotation_id for x in store.search("example")} == {"a1"}

    def test_search_by_value(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1", value="quantum physics"))
        store.add(_ann("a2", "http://x/2", value="classical mechanics"))
        assert {x.annotation_id for x in store.search("quantum")} == {"a1"}

    def test_search_case_insensitive(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1", value="Hello World"))
        assert {x.annotation_id for x in store.search("hello")} == {"a1"}

    def test_search_no_match(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1", value="apple"))
        assert store.search("cherry") == []

    def test_search_ignores_non_string_value(self, store: AnnotationStore) -> None:
        """Non-str values (int, dict) must not crash the search."""
        store.add(_ann("a1", "http://x/1", value=42))
        store.add(_ann("a2", "http://x/2", value={"k": "needle"}))
        # 42 and dict are not str -> only url matching applies
        assert store.search("needle") == []

    def test_search_unicode(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1", value="café au lait"))
        assert {x.annotation_id for x in store.search("CAFÉ")} == {"a1"}

    def test_search_empty_query_matches_all(self, store: AnnotationStore) -> None:
        """Empty substring matches every url -> returns all annotations."""
        store.add(_ann("a1", "http://x/1"))
        store.add(_ann("a2", "http://x/2"))
        assert len(store.search("")) == 2

    def test_search_none_raises(self, store: AnnotationStore) -> None:
        """None is not a str query; must be rejected (any exception)."""
        store.add(_ann("a1", "http://x/1"))
        with pytest.raises(Exception):
            store.search(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# count / get_stats
# ---------------------------------------------------------------------------


class TestStats:
    def test_count_empty(self, store: AnnotationStore) -> None:
        assert store.count == 0

    def test_count_tracks_adds(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1"))
        store.add(_ann("a2", "http://x/2"))
        assert store.count == 2

    def test_get_stats_empty(self, store: AnnotationStore) -> None:
        assert store.get_stats() == {"total": 0, "by_type": {}, "urls_annotated": 0}

    def test_get_stats_by_type(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1", AnnotationType.NOTE))
        store.add(_ann("a2", "http://x/1", AnnotationType.NOTE))
        store.add(_ann("a3", "http://x/2", AnnotationType.HIGHLIGHT))
        stats = store.get_stats()
        assert stats["total"] == 3
        assert stats["by_type"] == {"note": 2, "highlight": 1}
        assert stats["urls_annotated"] == 2

    def test_urls_annotated_excludes_empty_index_after_upsert(self, store: AnnotationStore) -> None:
        """After upserting id 'a' from u1 to u2, u1 has no annotations and must
        not be counted in urls_annotated."""
        store.add(_ann("a", "http://u1"))
        store.add(_ann("a", "http://u2"))  # reconciliation empties u1's index
        assert store.get_by_url("http://u1") == []
        stats = store.get_stats()
        assert stats["urls_annotated"] == 1  # only u2 actually has an annotation

    def test_urls_annotated_excludes_empty_index_after_remove(self, store: AnnotationStore) -> None:
        store.add(_ann("a", "http://u1"))
        store.add(_ann("b", "http://u1"))
        store.remove("a")
        store.remove("b")
        assert store.get_by_url("http://u1") == []
        assert store.get_stats()["urls_annotated"] == 0


# ---------------------------------------------------------------------------
# Annotation dataclass: update / to_dict
# ---------------------------------------------------------------------------


class TestAnnotationDataclass:
    def test_to_dict_round_trip_fields(self) -> None:
        a = _ann("a1", "http://x/1", AnnotationType.HIGHLIGHT, value="v", metadata={"k": 1}, author="me")
        d = a.to_dict()
        assert d["annotation_id"] == "a1"
        assert d["url"] == "http://x/1"
        assert d["type"] == "highlight"
        assert d["value"] == "v"
        assert d["metadata"] == {"k": 1}
        assert d["author"] == "me"
        assert isinstance(d["created_at"], float)

    def test_to_dict_type_is_string_value(self) -> None:
        a = _ann("a1", "http://x/1", AnnotationType.BOOKMARK)
        assert a.to_dict()["type"] == "bookmark"

    def test_annotation_update_sets_updated_at(self) -> None:
        a = _ann("a1", "http://x/1")
        assert a.updated_at is None
        a.update(value="x")
        assert a.updated_at is not None

    def test_annotation_update_merges_metadata(self) -> None:
        a = _ann("a1", "http://x/1", metadata={"a": 1})
        a.update(metadata={"b": 2})
        assert a.metadata == {"a": 1, "b": 2}

    def test_annotation_update_none_value_noop(self) -> None:
        a = _ann("a1", "http://x/1", value="keep")
        a.update(value=None)
        assert a.value == "keep"

    def test_annotation_default_metadata_isolated(self) -> None:
        """Two annotations must not share a mutable default metadata dict."""
        a1 = _ann("a1", "http://x/1")
        a2 = _ann("a2", "http://x/2")
        a1.metadata["k"] = "v"
        assert "k" not in a2.metadata


# ---------------------------------------------------------------------------
# Idempotence / property checks
# ---------------------------------------------------------------------------


class TestIdempotenceAndProperties:
    def test_add_same_object_twice_no_index_dup(self, store: AnnotationStore) -> None:
        a = _ann("a1", "http://x/1")
        store.add(a)
        store.add(a)  # re-adding the same object
        assert len(store.get_by_url("http://x/1")) == 1
        assert store.count == 1

    def test_full_lifecycle(self, store: AnnotationStore) -> None:
        store.add(_ann("a1", "http://x/1", value="lifecycle"))
        assert store.get("a1") is not None
        assert store.update("a1", value="updated") is True
        assert store.search("lifecycle") == []  # value changed
        assert store.search("updated") != []
        assert store.remove("a1") is True
        assert store.get("a1") is None

    def test_duplicate_ids_collapse(self, store: AnnotationStore) -> None:
        """Same annotation_id added repeatedly collapses to one entry."""
        for _ in range(5):
            store.add(_ann("a1", "http://x/1"))
        assert store.count == 1
        assert len(store.get_by_url("http://x/1")) == 1


# ---------------------------------------------------------------------------
# End-to-end CLI smoke
# ---------------------------------------------------------------------------


class TestEndToEndCLI:
    def test_cli_help(self) -> None:
        """The installed CLI must be importable and not crash on --help."""
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert "Traceback" not in result.stderr, f"CLI crashed: {result.stderr}"
        assert result.returncode == 0
