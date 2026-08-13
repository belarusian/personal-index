"""Tests for content_pin module - ContentPinner class."""

import json
import os

import pytest

from personal_index.content_pin import (
    ContentPinner,
    PinnedItem,
    pin_content,
    unpin_content,
)


class TestPinnedItem:
    """Tests for the PinnedItem dataclass."""

    def test_create_pinned_item(self):
        item = PinnedItem(item_id="test-1")
        assert item.item_id == "test-1"
        assert item.pinned_at != ""
        assert item.reason == ""
        assert item.metadata == {}

    def test_create_pinned_item_with_reason(self):
        item = PinnedItem(item_id="test-1", reason="important")
        assert item.reason == "important"

    def test_create_pinned_item_with_metadata(self):
        meta = {"source": "api"}
        item = PinnedItem(item_id="test-1", metadata=meta)
        assert item.metadata == meta

    def test_pinned_item_sets_timestamp(self):
        item = PinnedItem(item_id="test-1")
        # Should be a valid ISO format string
        from datetime import datetime
        datetime.fromisoformat(item.pinned_at)


class TestContentPinner:
    """Tests for the ContentPinner class."""

    @pytest.fixture
    def tmp_storage(self, tmp_path):
        return str(tmp_path / "pinned.json")

    @pytest.fixture
    def pinner(self, tmp_storage):
        return ContentPinner(storage_path=tmp_storage)

    # -- pin() --
    def test_pin_returns_true(self, pinner):
        assert pinner.pin("item-1") is True

    def test_pin_with_reason(self, pinner):
        pinner.pin("item-1", reason="important")
        item = pinner._pinned["item-1"]
        assert item.reason == "important"

    def test_pin_with_metadata(self, pinner):
        meta = {"key": "value"}
        pinner.pin("item-1", metadata=meta)
        item = pinner._pinned["item-1"]
        assert item.metadata == meta

    def test_pin_overwrites_existing(self, pinner):
        pinner.pin("item-1", reason="first")
        pinner.pin("item-1", reason="second")
        item = pinner._pinned["item-1"]
        assert item.reason == "second"

    def test_pin_multiple_items(self, pinner):
        pinner.pin("item-1")
        pinner.pin("item-2")
        pinner.pin("item-3")
        assert len(pinner._pinned) == 3

    # -- unpin() --
    def test_unpin_returns_true(self, pinner):
        pinner.pin("item-1")
        assert pinner.unpin("item-1") is True

    def test_unpin_removes_item(self, pinner):
        pinner.pin("item-1")
        pinner.unpin("item-1")
        assert "item-1" not in pinner._pinned

    def test_unpin_nonexistent_returns_true(self, pinner):
        assert pinner.unpin("nonexistent") is True

    def test_unpin_does_not_affect_others(self, pinner):
        pinner.pin("item-1")
        pinner.pin("item-2")
        pinner.unpin("item-1")
        assert "item-2" in pinner._pinned
        assert "item-1" not in pinner._pinned

    # -- is_pinned() --
    def test_is_pinned_true(self, pinner):
        pinner.pin("item-1")
        assert pinner.is_pinned("item-1") is True

    def test_is_pinned_false(self, pinner):
        assert pinner.is_pinned("nonexistent") is False

    def test_is_pinned_after_unpin(self, pinner):
        pinner.pin("item-1")
        pinner.unpin("item-1")
        assert pinner.is_pinned("item-1") is False

    # -- get_pinned_items() --
    def test_get_pinned_items_empty(self, pinner):
        assert pinner.get_pinned_items() == []

    def test_get_pinned_items_returns_list(self, pinner):
        pinner.pin("item-1")
        items = pinner.get_pinned_items()
        assert isinstance(items, list)
        assert len(items) == 1

    def test_get_pinned_items_multiple(self, pinner):
        pinner.pin("item-1")
        pinner.pin("item-2")
        items = pinner.get_pinned_items()
        ids = [i.item_id for i in items]
        assert "item-1" in ids
        assert "item-2" in ids

    # -- pin_order --
    def test_pin_order_preserved(self, pinner):
        pinner.pin("first")
        pinner.pin("second")
        pinner.pin("third")
        items = pinner.get_pinned_items()
        assert items[0].item_id == "first"
        assert items[1].item_id == "second"
        assert items[2].item_id == "third"

    # -- persistence to/from JSON --
    def test_persistence_saves_to_file(self, pinner, tmp_storage):
        pinner.pin("item-1", reason="test")
        assert os.path.exists(tmp_storage)
        with open(tmp_storage) as f:
            data = json.load(f)
        assert "item-1" in data
        assert data["item-1"]["reason"] == "test"

    def test_persistence_loads_from_file(self, tmp_storage):
        # Write data directly
        data = {
            "item-1": {
                "pinned_at": "2024-01-01T00:00:00",
                "reason": "loaded",
                "metadata": {},
            }
        }
        with open(tmp_storage, "w") as f:
            json.dump(data, f)
        # Load via ContentPinner
        pinner = ContentPinner(storage_path=tmp_storage)
        assert pinner.is_pinned("item-1")
        assert pinner._pinned["item-1"].reason == "loaded"

    def test_persistence_empty_file(self, tmp_storage):
        with open(tmp_storage, "w") as f:
            json.dump({}, f)
        pinner = ContentPinner(storage_path=tmp_storage)
        assert len(pinner.get_pinned_items()) == 0

    def test_persistence_corrupt_file(self, tmp_storage):
        with open(tmp_storage, "w") as f:
            f.write("not valid json{{{")
        pinner = ContentPinner(storage_path=tmp_storage)
        assert len(pinner.get_pinned_items()) == 0

    def test_persistence_creates_parent_dirs(self, tmp_path):
        storage = str(tmp_path / "sub" / "dir" / "pinned.json")
        pinner = ContentPinner(storage_path=storage)
        pinner.pin("item-1")
        assert os.path.exists(storage)

    # -- clear() --
    def test_clear_removes_all(self, pinner):
        pinner.pin("item-1")
        pinner.pin("item-2")
        pinner.clear()
        assert len(pinner.get_pinned_items()) == 0

    def test_clear_empty(self, pinner):
        pinner.clear()
        assert len(pinner.get_pinned_items()) == 0

    # -- module-level convenience functions --
    def test_module_pin_content(self):
        assert pin_content("module-test") is True

    def test_module_unpin_content(self):
        assert unpin_content("module-test") is True
