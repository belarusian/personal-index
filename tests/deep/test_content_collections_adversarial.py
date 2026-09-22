"""Adversarial deep tests for personal_index.content_collections.

Contract source: docs/content-collections.md + module docstrings.

The module maintains TWO views that must stay in sync:
  * the forward list  ``Collection.item_ids`` (ordered, deduplicated), and
  * the reverse index ``CollectionManager._item_to_collections``
    (item_id -> list of collection_ids containing it).

Every mutation (add_item / remove_item / move_item / merge / delete /
clear_items / deserialize) must keep the reverse index exactly equal to the
projection of the forward lists, with no empty list entries left behind.
These tests pin that invariant plus the documented guard paths, the
dedup/order semantics, the to_dict/from_dict round-trip, the get_recent
``limit <= 0 -> []`` guard, and the documented move_item multi-collection
semantic (removes from the named source only, not every collection).
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.content_collections import Collection, CollectionManager


# ---------------------------------------------------------------------------
# invariant helper
# ---------------------------------------------------------------------------

def _assert_reverse_index_consistent(m: CollectionManager) -> None:
    """The reverse index must equal the projection of the forward lists,
    with no empty list entries and no stale collection ids."""
    expected: dict[str, set[str]] = {}
    for cid, c in m._collections.items():
        for iid in c.item_ids:
            expected.setdefault(iid, set()).add(cid)

    # every reverse-index entry matches the forward projection
    for iid, cids in m._item_to_collections.items():
        assert set(cids) == expected.get(iid, set()), (
            f"reverse index desync for {iid!r}: "
            f"index={set(cids)} forward={expected.get(iid)}"
        )
        assert cids, f"empty reverse-index list left behind for {iid!r}"

    # every forward item is present in the reverse index
    for iid, exp_cids in expected.items():
        assert set(m._item_to_collections.get(iid, [])) == exp_cids, (
            f"missing reverse-index entry for {iid!r}: "
            f"index={m._item_to_collections.get(iid)} forward={exp_cids}"
        )


# ---------------------------------------------------------------------------
# Collection dataclass
# ---------------------------------------------------------------------------

def test_collection_defaults():
    c = Collection(name="n")
    assert c.name == "n"
    assert c.description == ""
    assert c.item_ids == []
    assert c.is_public is False
    assert c.updated_at is None
    assert len(c.collection_id) == 12


def test_collection_add_item_dedup():
    c = Collection(name="n")
    c.add_item("a")
    c.add_item("a")  # duplicate -> no-op
    assert c.item_ids == ["a"]
    assert c.item_count() == 1


def test_collection_add_item_order_preserved():
    c = Collection(name="n")
    for iid in ["c", "a", "b"]:
        c.add_item(iid)
    assert c.item_ids == ["c", "a", "b"]


def test_collection_add_item_refreshes_updated_at():
    c = Collection(name="n")
    assert c.updated_at is None
    c.add_item("a")
    assert c.updated_at is not None


def test_collection_add_duplicate_no_updated_refresh():
    c = Collection(name="n")
    c.add_item("a")
    first = c.updated_at
    c.add_item("a")  # no-op: must not refresh
    assert c.updated_at == first


def test_collection_remove_item_present():
    c = Collection(name="n")
    c.add_item("a")
    c.add_item("b")
    c.remove_item("a")
    assert c.item_ids == ["b"]


def test_collection_remove_absent_is_noop():
    c = Collection(name="n")
    c.add_item("a")
    before = c.updated_at
    c.remove_item("zzz")  # absent -> no-op, no refresh
    assert c.item_ids == ["a"]
    assert c.updated_at == before


def test_collection_contains():
    c = Collection(name="n")
    c.add_item("a")
    assert c.contains("a") is True
    assert c.contains("b") is False


def test_collection_unicode_item_ids():
    c = Collection(name="ünïcode")
    for iid in ["café", "日本語", "emoji🚀", ""]:
        c.add_item(iid)
    assert c.item_ids == ["café", "日本語", "emoji🚀", ""]
    assert c.contains("café") is True


def test_collection_to_dict_from_dict_roundtrip():
    c = Collection(name="n", description="d", is_public=True)
    c.add_item("a")
    c.add_item("b")
    d = c.to_dict()
    c2 = Collection.from_dict(d)
    assert c2.name == "n"
    assert c2.description == "d"
    assert c2.is_public is True
    assert c2.item_ids == ["a", "b"]
    assert c2.collection_id == c.collection_id
    assert c2.created_at == c.created_at
    assert c2.updated_at == c.updated_at


def test_collection_from_dict_missing_optional_fields():
    c = Collection.from_dict({"name": "only-name"})
    assert c.name == "only-name"
    assert c.description == ""
    assert c.item_ids == []
    assert c.is_public is False
    assert c.updated_at is None
    assert len(c.collection_id) == 12


def test_collection_from_dict_created_at_datetime_coerced():
    from datetime import datetime, timezone

    c = Collection.from_dict(
        {"name": "n", "created_at": datetime.now(timezone.utc)}
    )
    assert isinstance(c.created_at, str)
    assert "T" in c.created_at


def test_collection_to_dict_copies_item_ids():
    c = Collection(name="n")
    c.add_item("a")
    d = c.to_dict()
    d["item_ids"].append("mutated")
    assert c.item_ids == ["a"]  # to_dict returns a copy, not the live list


# ---------------------------------------------------------------------------
# CollectionManager — basic
# ---------------------------------------------------------------------------

def test_manager_create_and_get():
    m = CollectionManager()
    cid = m.create("A")
    assert m.get(cid) is not None
    assert m.get(cid).name == "A"
    assert m.count() == 1


def test_manager_get_missing_returns_none():
    m = CollectionManager()
    assert m.get("nope") is None


def test_manager_list_public_private_partition():
    m = CollectionManager()
    m.create("pub", is_public=True)
    m.create("priv")
    m.create("pub2", is_public=True)
    assert len(m.list_public()) == 2
    assert len(m.list_private()) == 1
    assert len(m.list_all()) == 3
    # public + private == total
    assert len(m.list_public()) + len(m.list_private()) == m.count()


def test_manager_get_items_missing_collection():
    m = CollectionManager()
    assert m.get_items("nope") == []


def test_manager_get_collections_for_item_missing():
    m = CollectionManager()
    assert m.get_collections_for_item("nope") == []


# ---------------------------------------------------------------------------
# CollectionManager — add / remove + reverse index
# ---------------------------------------------------------------------------

def test_add_item_guard_path_missing_collection():
    m = CollectionManager()
    assert m.add_item("nope", "x") is False
    assert m._item_to_collections == {}  # untouched
    _assert_reverse_index_consistent(m)


def test_add_item_updates_reverse_index():
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    assert m.add_item(a, "x") is True
    assert m.add_item(b, "x") is True
    assert set(m._item_to_collections["x"]) == {a, b}
    assert len(m.get_collections_for_item("x")) == 2
    _assert_reverse_index_consistent(m)


def test_add_item_idempotent_reverse_index():
    m = CollectionManager()
    a = m.create("A")
    m.add_item(a, "x")
    m.add_item(a, "x")  # duplicate
    assert m._item_to_collections["x"] == [a]  # no duplicate cid
    _assert_reverse_index_consistent(m)


def test_add_items_batch():
    m = CollectionManager()
    a = m.create("A")
    m.add_items(a, ["x", "y", "z"])
    assert m.get_items(a) == ["x", "y", "z"]
    _assert_reverse_index_consistent(m)


def test_remove_item_updates_reverse_index():
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    m.add_item(a, "x")
    m.add_item(b, "x")
    assert m.remove_item(a, "x") is True
    assert m._item_to_collections["x"] == [b]
    _assert_reverse_index_consistent(m)


def test_remove_item_last_collection_deletes_index_entry():
    m = CollectionManager()
    a = m.create("A")
    m.add_item(a, "x")
    m.remove_item(a, "x")
    assert "x" not in m._item_to_collections  # entry deleted, not left empty
    _assert_reverse_index_consistent(m)


def test_remove_item_guard_path_missing_collection():
    m = CollectionManager()
    assert m.remove_item("nope", "x") is False
    assert m._item_to_collections == {}
    _assert_reverse_index_consistent(m)


def test_remove_absent_item_returns_true_but_no_index_change():
    m = CollectionManager()
    a = m.create("A")
    m.add_item(a, "y")
    # removing an item that was never added: collection exists -> True,
    # but no reverse-index entry is created for it
    assert m.remove_item(a, "never") is True
    assert "never" not in m._item_to_collections
    _assert_reverse_index_consistent(m)


# ---------------------------------------------------------------------------
# move_item — documented multi-collection semantic
# ---------------------------------------------------------------------------

def test_move_item_relocates_from_every_collection():
    """move_item removes from EVERY collection the item belongs to, then adds to dest
    (Option A: true relocation)."""
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    c = m.create("C")
    m.add_item(a, "x")
    m.add_item(b, "x")
    m.add_item(c, "x")
    assert m.move_item("x", a, c) is True
    # removed from a, present in b and c
    assert "x" not in m.get_items(a)
    assert "x" not in m.get_items(b)
    assert "x" in m.get_items(c)
    # reverse index: x -> {b, c}
    assert set(m._item_to_collections["x"]) == {c}
    _assert_reverse_index_consistent(m)


def test_move_item_to_collection_that_already_has_it():
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    m.add_item(a, "x")
    m.add_item(b, "x")
    assert m.move_item("x", a, b) is True
    assert "x" not in m.get_items(a)
    assert m.get_items(b).count("x") == 1  # dedup, not doubled
    assert m._item_to_collections["x"] == [b]
    _assert_reverse_index_consistent(m)


def test_move_item_missing_source_returns_false():
    m = CollectionManager()
    b = m.create("B")
    m.add_item(b, "x")
    assert m.move_item("x", "nope", b) is False
    _assert_reverse_index_consistent(m)


def test_move_item_missing_dest_returns_false():
    m = CollectionManager()
    a = m.create("A")
    m.add_item(a, "x")
    assert m.move_item("x", a, "nope") is False
    # item stays in a
    assert "x" in m.get_items(a)
    _assert_reverse_index_consistent(m)


def test_move_item_item_not_in_source_still_adds_to_dest():
    """The item need not be in the source; it is still added to the dest."""
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    assert m.move_item("x", a, b) is True
    assert m.get_items(b) == ["x"]
    assert m.get_items(a) == []
    _assert_reverse_index_consistent(m)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

def test_merge_self_merge_is_noop():
    m = CollectionManager()
    a = m.create("A")
    m.add_item(a, "x")
    assert m.merge(a, a) is False
    # collection survives, item survives
    assert m.get(a) is not None
    assert m.get_items(a) == ["x"]
    _assert_reverse_index_consistent(m)


def test_merge_moves_items_and_deletes_source():
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    m.add_item(a, "x")
    m.add_item(a, "y")
    m.add_item(b, "y")  # overlap
    assert m.merge(b, a) is True
    assert m.get(a) is None  # source deleted
    assert set(m.get_items(b)) == {"x", "y"}
    assert m.get_items(b).count("y") == 1  # dedup
    _assert_reverse_index_consistent(m)


def test_merge_missing_source_returns_false():
    m = CollectionManager()
    b = m.create("B")
    assert m.merge(b, "nope") is False
    _assert_reverse_index_consistent(m)


def test_merge_missing_target_returns_false():
    m = CollectionManager()
    a = m.create("A")
    m.add_item(a, "x")
    assert m.merge("nope", a) is False
    # source survives
    assert m.get(a) is not None
    _assert_reverse_index_consistent(m)


# ---------------------------------------------------------------------------
# delete / clear_items
# ---------------------------------------------------------------------------

def test_delete_cleans_reverse_index():
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    m.add_item(a, "x")
    m.add_item(b, "x")
    assert m.delete(a) is True
    assert m.get(a) is None
    assert m._item_to_collections["x"] == [b]
    _assert_reverse_index_consistent(m)


def test_delete_last_collection_removes_index_entry():
    m = CollectionManager()
    a = m.create("A")
    m.add_item(a, "x")
    m.delete(a)
    assert "x" not in m._item_to_collections
    _assert_reverse_index_consistent(m)


def test_delete_missing_returns_false():
    m = CollectionManager()
    assert m.delete("nope") is False
    _assert_reverse_index_consistent(m)


def test_clear_items_keeps_collection_cleans_index():
    m = CollectionManager()
    a = m.create("A")
    m.add_item(a, "x")
    m.add_item(a, "y")
    assert m.clear_items(a) is True
    assert m.get(a) is not None
    assert m.get_items(a) == []
    assert "x" not in m._item_to_collections
    assert "y" not in m._item_to_collections
    _assert_reverse_index_consistent(m)


def test_clear_items_guard_path_missing():
    m = CollectionManager()
    assert m.clear_items("nope") is False
    _assert_reverse_index_consistent(m)


# ---------------------------------------------------------------------------
# get_recent — negative-slice "top N" guard (N <= 0 -> [])
# ---------------------------------------------------------------------------

def test_get_recent_default():
    m = CollectionManager()
    for i in range(5):
        m.create(f"c{i}")
    assert len(m.get_recent()) == 5


def test_get_recent_limit_zero_returns_empty():
    m = CollectionManager()
    for i in range(5):
        m.create(f"c{i}")
    assert m.get_recent(0) == []


def test_get_recent_limit_negative_returns_empty():
    """Negative-slice top-N class: limit < 0 must return [] (not all-but-last)."""
    m = CollectionManager()
    for i in range(5):
        m.create(f"c{i}")
    assert m.get_recent(-1) == []
    assert m.get_recent(-100) == []


def test_get_recent_limit_larger_than_count():
    m = CollectionManager()
    for i in range(3):
        m.create(f"c{i}")
    assert len(m.get_recent(100)) == 3


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

def test_get_stats_empty():
    m = CollectionManager()
    s = m.get_stats()
    assert s == {
        "total_collections": 0,
        "total_items": 0,
        "public_collections": 0,
        "private_collections": 0,
    }


def test_get_stats_counts_items_per_collection():
    """total_items is the PER-COLLECTION sum: an item in N collections is
    counted N times (documented, not distinct)."""
    m = CollectionManager()
    a = m.create("A", is_public=True)
    b = m.create("B")
    m.add_item(a, "x")
    m.add_item(b, "x")  # x in 2 collections
    m.add_item(a, "y")
    s = m.get_stats()
    assert s["total_collections"] == 2
    assert s["total_items"] == 3  # a:2 + b:1
    assert s["public_collections"] == 1
    assert s["private_collections"] == 1


# ---------------------------------------------------------------------------
# serialize / deserialize round-trip
# ---------------------------------------------------------------------------

def test_serialize_deserialize_roundtrip():
    m = CollectionManager()
    a = m.create("A", description="d", is_public=True)
    b = m.create("B")
    m.add_item(a, "x")
    m.add_item(a, "y")
    m.add_item(b, "x")
    data = m.serialize()
    m2 = CollectionManager()
    m2.deserialize(data)
    assert m2.count() == 2
    assert set(m2.get_items(a)) == {"x", "y"}
    assert m2.get_items(b) == ["x"]
    assert m2.get(a).is_public is True
    assert m2.get(a).description == "d"
    # reverse index rebuilt correctly
    assert set(m2._item_to_collections["x"]) == {a, b}
    _assert_reverse_index_consistent(m2)


def test_deserialize_empty_list():
    m = CollectionManager()
    m.create("A")
    m.deserialize([])
    assert m.count() == 0
    assert m._item_to_collections == {}
    _assert_reverse_index_consistent(m)


def test_deserialize_rebuilds_reverse_index():
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    m.add_item(a, "x")
    m.add_item(b, "x")
    data = m.serialize()
    m2 = CollectionManager()
    m2.deserialize(data)
    assert set(m2._item_to_collections["x"]) == {a, b}
    _assert_reverse_index_consistent(m2)


# ---------------------------------------------------------------------------
# property: invariant survives a randomized mutation sequence
# ---------------------------------------------------------------------------

def test_reverse_index_invariant_under_random_ops():
    import random

    random.seed(198)
    m = CollectionManager()
    cids = [m.create(f"c{i}") for i in range(4)]
    items = [f"i{j}" for j in range(8)]
    for _ in range(300):
        op = random.randrange(6)
        cid = random.choice(cids)
        iid = random.choice(items)
        if op == 0:
            m.add_item(cid, iid)
        elif op == 1:
            m.remove_item(cid, iid)
        elif op == 2:
            m.move_item(iid, random.choice(cids), random.choice(cids))
        elif op == 3:
            m.merge(random.choice(cids), random.choice(cids))
        elif op == 4:
            m.clear_items(cid)
        else:
            m.delete(cid)
        _assert_reverse_index_consistent(m)


# ---------------------------------------------------------------------------
# end-to-end CLI run
# ---------------------------------------------------------------------------

def test_cli_boots_and_collections_importable():
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    assert "Personal Index" in proc.stdout
    import personal_index.content_collections as cc  # noqa: F401

    assert callable(cc.CollectionManager.create)
    assert callable(cc.Collection.from_dict)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


def test_move_item_self_move_from_equals_to():
    """Adversarial: from_collection_id == to_collection_id (self-move).

    Option A: the item is removed from EVERY collection it belongs to, then
    re-added to the destination (which is the same collection). Postcondition:
    the item ends up in exactly one collection (the destination) and the
    reverse index agrees. An item also present in a third collection is
    relocated out of it.
    """
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    m.add_item(a, "x")
    m.add_item(b, "x")
    assert m.move_item("x", a, a) is True
    # relocated: x in a only, removed from b
    assert m.get_items(a) == ["x"]
    assert "x" not in m.get_items(b)
    assert m._item_to_collections["x"] == [a]
    _assert_reverse_index_consistent(m)


def test_move_item_item_in_dest_not_in_source():
    """Adversarial: item is in the destination and a third collection, but NOT
    in the named source. Option A still relocates: after the call the item is
    in exactly one collection (the destination), removed from the third.
    """
    m = CollectionManager()
    a = m.create("A")
    b = m.create("B")
    c = m.create("C")
    m.add_item(b, "y")
    m.add_item(c, "y")
    assert m.move_item("y", a, b) is True
    # relocated: y in b only, removed from c, a stays empty
    assert m.get_items(b) == ["y"]
    assert "y" not in m.get_items(c)
    assert m.get_items(a) == []
    assert m._item_to_collections["y"] == [b]
    _assert_reverse_index_consistent(m)


# ---------------------------------------------------------------------------
# Cycle 367: additional adversarial pins for functions not previously covered
# ---------------------------------------------------------------------------

def test_update_name_success():
    """update_name sets name and refreshes updated_at; returns True."""
    mgr = CollectionManager()
    cid = mgr.create("My Col")
    old_updated = mgr.get(cid).updated_at
    import time; time.sleep(0.01)
    assert mgr.update_name(cid, "Renamed") is True
    c = mgr.get(cid)
    assert c.name == "Renamed"
    assert c.updated_at is not None
    assert c.updated_at != old_updated


def test_update_name_missing_collection_returns_false():
    """update_name on a non-existent collection returns False, no side effects."""
    mgr = CollectionManager()
    assert mgr.update_name("nonexistent", "X") is False
    assert mgr.count() == 0


def test_update_name_empty_string():
    """update_name with empty string is valid (name becomes '')."""
    mgr = CollectionManager()
    cid = mgr.create("Original")
    assert mgr.update_name(cid, "") is True
    assert mgr.get(cid).name == ""


def test_update_name_unicode():
    """update_name with unicode characters works."""
    mgr = CollectionManager()
    cid = mgr.create("test")
    assert mgr.update_name(cid, "Ünïcödé 集合 📚") is True
    assert mgr.get(cid).name == "Ünïcödé 集合 📚"


def test_update_description_success():
    """update_description sets description and refreshes updated_at."""
    mgr = CollectionManager()
    cid = mgr.create("Col")
    old_updated = mgr.get(cid).updated_at
    import time; time.sleep(0.01)
    assert mgr.update_description(cid, "A description") is True
    c = mgr.get(cid)
    assert c.description == "A description"
    assert c.updated_at != old_updated


def test_update_description_missing_collection():
    """update_description on non-existent collection returns False."""
    mgr = CollectionManager()
    assert mgr.update_description("nope", "desc") is False


def test_update_description_empty_string():
    """update_description with empty string is valid."""
    mgr = CollectionManager()
    cid = mgr.create("Col")
    assert mgr.update_description(cid, "") is True
    assert mgr.get(cid).description == ""


def test_rename_is_alias_for_update_name():
    """rename() is an alias for update_name() - same behavior."""
    mgr = CollectionManager()
    cid = mgr.create("Before")
    assert mgr.rename(cid, "After") is True
    assert mgr.get(cid).name == "After"


def test_rename_missing_collection():
    """rename on non-existent collection returns False."""
    mgr = CollectionManager()
    assert mgr.rename("ghost", "X") is False


def test_toggle_public_flips_and_refreshes():
    """toggle_public flips is_public and refreshes updated_at."""
    mgr = CollectionManager()
    cid = mgr.create("Col")
    assert mgr.get(cid).is_public is False
    old_updated = mgr.get(cid).updated_at
    import time; time.sleep(0.01)
    assert mgr.toggle_public(cid) is True
    assert mgr.get(cid).is_public is True
    assert mgr.get(cid).updated_at != old_updated
    # Toggle back
    assert mgr.toggle_public(cid) is True
    assert mgr.get(cid).is_public is False


def test_toggle_public_missing_collection():
    """toggle_public on non-existent collection returns False."""
    mgr = CollectionManager()
    assert mgr.toggle_public("nope") is False


def test_search_by_name_case_insensitive():
    """search matches name case-insensitively."""
    mgr = CollectionManager()
    mgr.create("Python Tips")
    mgr.create("Java Notes")
    results = mgr.search("python")
    assert len(results) == 1
    assert results[0].name == "Python Tips"


def test_search_by_description():
    """search matches description text."""
    mgr = CollectionManager()
    mgr.create("Col A", description="about databases")
    mgr.create("Col B", description="about networks")
    results = mgr.search("databases")
    assert len(results) == 1
    assert results[0].name == "Col A"


def test_search_no_match_returns_empty():
    """search with no match returns empty list."""
    mgr = CollectionManager()
    mgr.create("Alpha")
    assert mgr.search("zzz") == []


def test_search_empty_query_matches_all():
    """search with empty string matches every collection (substring of all)."""
    mgr = CollectionManager()
    mgr.create("A")
    mgr.create("B")
    results = mgr.search("")
    assert len(results) == 2


def test_search_unicode_query():
    """search with unicode query works."""
    mgr = CollectionManager()
    mgr.create("日本語コレクション")
    results = mgr.search("日本語")
    assert len(results) == 1


def test_count_empty_manager():
    """count returns 0 for an empty manager."""
    mgr = CollectionManager()
    assert mgr.count() == 0


def test_count_after_create_and_delete():
    """count reflects creates and deletes correctly."""
    mgr = CollectionManager()
    c1 = mgr.create("A")
    c2 = mgr.create("B")
    assert mgr.count() == 2
    mgr.delete(c1)
    assert mgr.count() == 1
    mgr.delete(c2)
    assert mgr.count() == 0


def test_collection_item_count_property():
    """Collection.item_count returns len(item_ids)."""
    c = Collection(name="Test")
    assert c.item_count == 0
    c.add_item("x")
    c.add_item("y")
    c.add_item("x")  # dedup
    assert c.item_count == 2
    c.remove_item("x")
    assert c.item_count == 1
