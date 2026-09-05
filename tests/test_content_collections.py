"""Tests for content_collections module - group items into collections."""

from __future__ import annotations

from personal_index.content_collections import (
    Collection,
    CollectionManager,
)


class TestCollection:
    """Tests for Collection dataclass."""

    def test_create_collection_basic(self):
        c = Collection(name="My Reading List")
        assert c.name == "My Reading List"
        assert c.item_ids == []
        assert c.description == ""
        assert c.created_at is not None

    def test_create_collection_with_fields(self):
        c = Collection(
            name="Research",
            description="Academic papers",
            item_ids=["i1", "i2"],
            is_public=True,
        )
        assert c.description == "Academic papers"
        assert c.item_ids == ["i1", "i2"]
        assert c.is_public is True

    def test_collection_to_dict(self):
        c = Collection(name="Tech", description="Tech articles", item_ids=["a"])
        d = c.to_dict()
        assert d["name"] == "Tech"
        assert d["description"] == "Tech articles"
        assert d["item_ids"] == ["a"]

    def test_collection_from_dict(self):
        data = {
            "collection_id": "c1",
            "name": "Saved",
            "description": "Saved items",
            "item_ids": ["x", "y"],
            "is_public": False,
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T00:00:00+00:00",
        }
        c = Collection.from_dict(data)
        assert c.collection_id == "c1"
        assert c.name == "Saved"
        assert c.item_ids == ["x", "y"]
        assert c.is_public is False

    def test_collection_from_dict_defaults(self):
        data = {"name": "Default"}
        c = Collection.from_dict(data)
        assert c.description == ""
        assert c.item_ids == []
        assert c.is_public is False

    def test_collection_add_item(self):
        c = Collection(name="Test")
        c.add_item("item1")
        assert "item1" in c.item_ids

    def test_collection_add_duplicate_item(self):
        c = Collection(name="Test")
        c.add_item("item1")
        c.add_item("item1")
        assert c.item_ids.count("item1") == 1

    def test_collection_remove_item(self):
        c = Collection(name="Test", item_ids=["a", "b", "c"])
        c.remove_item("b")
        assert "b" not in c.item_ids
        assert "a" in c.item_ids

    def test_collection_remove_nonexistent_item(self):
        c = Collection(name="Test", item_ids=["a"])
        c.remove_item("z")
        assert "a" in c.item_ids

    def test_collection_contains_item(self):
        c = Collection(name="Test", item_ids=["a", "b"])
        assert c.contains("a") is True
        assert c.contains("z") is False

    def test_collection_item_count(self):
        c = Collection(name="Test", item_ids=["a", "b", "c"])
        assert c.item_count() == 3

    def test_collection_serialization_roundtrip(self):
        c = Collection(name="Round", description="Trip", item_ids=["1", "2"], is_public=True)
        d = c.to_dict()
        c2 = Collection.from_dict(d)
        assert c2.name == c.name
        assert c2.description == c.description
        assert c2.item_ids == c.item_ids
        assert c2.is_public == c.is_public


class TestCollectionManager:
    """Tests for CollectionManager."""

    def setup_method(self):
        self.manager = CollectionManager()

    def test_create_collection(self):
        cid = self.manager.create("Reading List")
        assert cid is not None
        c = self.manager.get(cid)
        assert c is not None
        assert c.name == "Reading List"

    def test_create_collection_with_description(self):
        cid = self.manager.create(
            "Research", description="Academic papers", is_public=True
        )
        c = self.manager.get(cid)
        assert c.description == "Academic papers"
        assert c.is_public is True

    def test_get_collection(self):
        cid = self.manager.create("Test")
        c = self.manager.get(cid)
        assert c.name == "Test"

    def test_get_nonexistent_collection(self):
        c = self.manager.get("nonexistent")
        assert c is None

    def test_list_collections(self):
        self.manager.create("A")
        self.manager.create("B")
        self.manager.create("C")
        collections = self.manager.list_all()
        assert len(collections) == 3

    def test_list_public_collections(self):
        self.manager.create("Public", is_public=True)
        self.manager.create("Private", is_public=False)
        self.manager.create("Public2", is_public=True)
        public = self.manager.list_public()
        assert len(public) == 2

    def test_list_private_collections(self):
        self.manager.create("Public", is_public=True)
        self.manager.create("Private", is_public=False)
        private = self.manager.list_private()
        assert len(private) == 1

    def test_add_item_to_collection(self):
        cid = self.manager.create("Test")
        self.manager.add_item(cid, "item1")
        c = self.manager.get(cid)
        assert "item1" in c.item_ids

    def test_add_item_to_nonexistent_collection(self):
        result = self.manager.add_item("nonexistent", "item1")
        assert result is False

    def test_remove_item_from_collection(self):
        cid = self.manager.create("Test")
        self.manager.add_item(cid, "item1")
        self.manager.remove_item(cid, "item1")
        c = self.manager.get(cid)
        assert "item1" not in c.item_ids

    def test_remove_item_from_nonexistent_collection(self):
        result = self.manager.remove_item("nonexistent", "item1")
        assert result is False

    def test_update_collection_name(self):
        cid = self.manager.create("Old Name")
        self.manager.update_name(cid, "New Name")
        c = self.manager.get(cid)
        assert c.name == "New Name"

    def test_update_collection_description(self):
        cid = self.manager.create("Test")
        self.manager.update_description(cid, "New description")
        c = self.manager.get(cid)
        assert c.description == "New description"

    def test_update_nonexistent_collection(self):
        result = self.manager.update_name("nonexistent", "New")
        assert result is False

    def test_delete_collection(self):
        cid = self.manager.create("To Delete")
        self.manager.delete(cid)
        assert self.manager.get(cid) is None

    def test_delete_nonexistent_collection(self):
        result = self.manager.delete("nonexistent")
        assert result is False

    def test_get_items_in_collection(self):
        cid = self.manager.create("Test")
        self.manager.add_item(cid, "a")
        self.manager.add_item(cid, "b")
        items = self.manager.get_items(cid)
        assert items == ["a", "b"]

    def test_get_collections_for_item(self):
        cid1 = self.manager.create("Collection A")
        cid2 = self.manager.create("Collection B")
        self.manager.add_item(cid1, "item1")
        self.manager.add_item(cid2, "item1")
        collections = self.manager.get_collections_for_item("item1")
        assert len(collections) == 2

    def test_search_collections(self):
        self.manager.create("Reading List")
        self.manager.create("Research Papers")
        self.manager.create("News Articles")
        results = self.manager.search("research")
        assert len(results) == 1
        assert results[0].name == "Research Papers"

    def test_search_collections_no_results(self):
        self.manager.create("Test")
        results = self.manager.search("xyz")
        assert len(results) == 0

    def test_get_stats(self):
        cid = self.manager.create("Test")
        self.manager.add_item(cid, "a")
        self.manager.add_item(cid, "b")
        stats = self.manager.get_stats()
        assert stats["total_collections"] == 1
        assert stats["total_items"] == 2

    def test_move_item_between_collections(self):
        cid1 = self.manager.create("Source")
        cid2 = self.manager.create("Dest")
        self.manager.add_item(cid1, "item1")
        self.manager.move_item("item1", cid1, cid2)
        c1 = self.manager.get(cid1)
        c2 = self.manager.get(cid2)
        assert "item1" not in c1.item_ids
        assert "item1" in c2.item_ids

    def test_move_item_nonexistent_source(self):
        cid = self.manager.create("Dest")
        result = self.manager.move_item("item1", "nonexistent", cid)
        assert result is False

    def test_move_item_nonexistent_dest(self):
        cid = self.manager.create("Source")
        self.manager.add_item(cid, "item1")
        result = self.manager.move_item("item1", cid, "nonexistent")
        assert result is False

    def test_move_item_absent_from_source_still_adds_to_dest(self):
        # Pins the corrected docstring claim: move_item does NOT require the
        # item to be present in the source; it adds to dest and returns True
        # whenever both collections exist.
        cid_src = self.manager.create("Source")
        cid_dst = self.manager.create("Dest")
        # 'item1' is never added to the source collection.
        result = self.manager.move_item("item1", cid_src, cid_dst)
        assert result is True
        assert "item1" not in self.manager.get(cid_src).item_ids
        assert "item1" in self.manager.get(cid_dst).item_ids

    def test_merge_collections(self):
        cid1 = self.manager.create("A")
        cid2 = self.manager.create("B")
        self.manager.add_item(cid1, "a")
        self.manager.add_item(cid2, "b")
        self.manager.merge(cid1, cid2)
        c1 = self.manager.get(cid1)
        assert "a" in c1.item_ids
        assert "b" in c1.item_ids
        assert self.manager.get(cid2) is None

    def test_merge_nonexistent_collection(self):
        cid = self.manager.create("A")
        result = self.manager.merge(cid, "nonexistent")
        assert result is False

    def test_clear_collection(self):
        cid = self.manager.create("Test")
        self.manager.add_item(cid, "a")
        self.manager.add_item(cid, "b")
        self.manager.clear_items(cid)
        c = self.manager.get(cid)
        assert c.item_ids == []

    def test_serialize_deserialize(self):
        cid = self.manager.create("Test", description="Desc")
        self.manager.add_item(cid, "item1")
        data = self.manager.serialize()
        manager2 = CollectionManager()
        manager2.deserialize(data)
        assert len(manager2.list_all()) == 1
        c = manager2.list_all()[0]
        assert c.name == "Test"
        assert "item1" in c.item_ids

    def test_get_recent_collections(self):
        self.manager.create("First")
        self.manager.create("Second")
        self.manager.create("Third")
        recent = self.manager.get_recent(2)
        assert len(recent) == 2

    def test_rename_collection(self):
        cid = self.manager.create("Original")
        self.manager.rename(cid, "Renamed")
        c = self.manager.get(cid)
        assert c.name == "Renamed"

    def test_toggle_public(self):
        cid = self.manager.create("Test", is_public=False)
        self.manager.toggle_public(cid)
        c = self.manager.get(cid)
        assert c.is_public is True
        self.manager.toggle_public(cid)
        c = self.manager.get(cid)
        assert c.is_public is False

    def test_get_collection_count(self):
        self.manager.create("A")
        self.manager.create("B")
        assert self.manager.count() == 2

    def test_add_multiple_items(self):
        cid = self.manager.create("Test")
        self.manager.add_items(cid, ["a", "b", "c"])
        c = self.manager.get(cid)
        assert len(c.item_ids) == 3

    def test_remove_duplicate_items(self):
        cid = self.manager.create("Test")
        self.manager.add_items(cid, ["a", "a", "b"])
        c = self.manager.get(cid)
        assert c.item_ids.count("a") == 1


class TestCollectionAddItemIndexPinning:
    """Pin CollectionManager.add_item returned bool + observable index state."""

    def setup_method(self):
        self.manager = CollectionManager()

    def test_add_item_normal_pins_returned_bool_and_indexes(self):
        cid = self.manager.create("Test")
        result = self.manager.add_item(cid, "item1")
        # returned object: True on success
        assert result is True
        # index 1: Collection.item_ids contains the item
        c = self.manager.get(cid)
        assert "item1" in c.item_ids
        assert self.manager.get_items(cid) == ["item1"]
        # index 2: _item_to_collections reverse index resolves the collection
        for_coll = self.manager.get_collections_for_item("item1")
        assert [col.collection_id for col in for_coll] == [cid]

    def test_add_item_guard_path_pins_false_and_untouched_index(self):
        # guard path: nonexistent collection -> False, reverse index untouched
        result = self.manager.add_item("nonexistent", "item1")
        assert result is False
        # no collection was created for the item
        assert self.manager.get_collections_for_item("item1") == []


class TestCollectionGetStatsPinning:
    """Pin CollectionManager.get_stats returned dict fields (normal + guard)."""

    def setup_method(self):
        self.manager = CollectionManager()

    def test_get_stats_normal_pins_returned_dict_fields(self):
        # 2 public + 1 private collection; item "x" in TWO collections,
        # "y" in one -> total_items double-counts "x" (3, not 2 distinct).
        cid1 = self.manager.create("A", is_public=True)
        cid2 = self.manager.create("B", is_public=True)
        cid3 = self.manager.create("C", is_public=False)
        assert self.manager.get(cid3).is_public is False
        assert self.manager.add_item(cid1, "x") is True
        assert self.manager.add_item(cid2, "x") is True
        assert self.manager.add_item(cid1, "y") is True
        stats = self.manager.get_stats()
        # returned object: exactly the four documented keys
        assert set(stats.keys()) == {
            "total_collections", "total_items",
            "public_collections", "private_collections",
        }
        assert stats["total_collections"] == 3
        # per-collection sum: 2 (cid1) + 1 (cid2) + 0 (cid3) = 3,
        # NOT the 2 distinct items {x, y} -> pins the double-count semantics
        assert stats["total_items"] == 3
        assert stats["public_collections"] == 2
        assert stats["private_collections"] == 1
        # public + private partition total_collections
        assert stats["public_collections"] + stats["private_collections"] == \
            stats["total_collections"]

    def test_get_stats_empty_manager_guard_path_pins_all_zero(self):
        # guard path: no collections -> all four keys 0
        stats = self.manager.get_stats()
        assert stats == {
            "total_collections": 0,
            "total_items": 0,
            "public_collections": 0,
            "private_collections": 0,
        }
