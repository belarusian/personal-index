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

    def test_pin_returns_true_on_success(self, pinner):
        # Regression (TICKET-415, original claim "True if successfully
        # pinned."): the success path returns True. Re-pinning an
        # already-pinned id (overwrite) must still return True.
        assert pinner.pin("item-1") is True
        assert pinner.pin("item-1", reason="again") is True
        assert pinner.pin("item-1", metadata={"k": "v"}) is True
        assert pinner.is_pinned("item-1") is True

    def test_pin_returns_false_and_rolls_back_on_save_failure(self, pinner, monkeypatch):
        # Regression (TICKET-415, original claim "True if successfully
        # pinned."): when persistence fails (OSError in _save), pin()
        # returns False and the in-memory state is rolled back so the
        # item is not left pinned.
        def _boom():
            raise OSError("disk full")

        monkeypatch.setattr(pinner, "_save", _boom)
        assert pinner.pin("item-1") is False
        assert pinner.is_pinned("item-1") is False
        assert pinner.get_pinned_items() == []

    def test_pin_rollback_preserves_prior_items_on_save_failure(self, pinner, monkeypatch):
        # Regression (TICKET-415): a failed pin must not drop items that
        # were already pinned before the failed call.
        pinner.pin("existing")
        assert pinner.is_pinned("existing") is True

        def _boom():
            raise OSError("disk full")

        monkeypatch.setattr(pinner, "_save", _boom)
        assert pinner.pin("new-item") is False
        assert pinner.is_pinned("new-item") is False
        assert pinner.is_pinned("existing") is True

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

    def test_unpin_returns_false_and_rolls_back_on_save_failure(self, pinner, monkeypatch):
        # Regression (TICKET-426): the original claim is "True if
        # successfully unpinned (or was not pinned)." When persistence
        # fails (OSError in _save), unpin() returns False and the item
        # is restored to pinned state.
        pinner.pin("item-1")
        assert pinner.is_pinned("item-1") is True

        def fake_save():
            raise OSError("disk full")

        monkeypatch.setattr(pinner, "_save", fake_save)
        assert pinner.unpin("item-1") is False
        assert pinner.is_pinned("item-1") is True

    def test_unpin_noop_returns_true(self, pinner):
        # Unpinning a never-pinned id is a no-op and returns True.
        assert pinner.unpin("never-pinned") is True
        # Unpinning an already-unpinned id is also a no-op, still True.
        pinner.pin("item-1")
        assert pinner.unpin("item-1") is True
        assert pinner.unpin("item-1") is True

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


class TestModulePinContentDocstring:
    """TICKET-449: pin the corrected pin_content docstring against the
    returned object. The docstring now states the exact two-path behavior:
    True on success; False on persistence failure (OSError in _save) with the
    in-memory state rolled back so the item is not left pinned. Witness both
    the normal case (returns True, item pinned) and the guard path (returns
    False, item not left pinned)."""

    def test_module_pin_content_success_pins_item(self):
        """Normal case: pin_content returns True and the item is pinned."""
        import personal_index.content_pin as cp

        cp._default_pinner = ContentPinner(storage_path="/tmp/t448_pin.json")
        assert cp.pin_content("t448-item") is True
        assert cp._get_default_pinner().is_pinned("t448-item") is True

    def test_module_pin_content_false_rolls_back_on_save_failure(self, monkeypatch):
        """Guard path: when _save raises OSError, pin_content returns False
        and the item is not left pinned (rollback), matching the corrected
        docstring claim."""
        import personal_index.content_pin as cp

        cp._default_pinner = ContentPinner(storage_path="/tmp/t448_pin2.json")

        def _boom():
            raise OSError("disk full")

        monkeypatch.setattr(cp._default_pinner, "_save", _boom)
        assert cp.pin_content("t448-fail") is False
        assert cp._get_default_pinner().is_pinned("t448-fail") is False
        assert cp._get_default_pinner().get_pinned_items() == []


class TestContentPinnerNonDictJSON:
    """Regression tests for TICKET-266: non-dict JSON in storage file."""

    def test_null_storage_resets_to_empty(self, tmp_path):
        path = str(tmp_path / "pinned.json")
        with open(path, "w") as f:
            f.write("null")
        pinner = ContentPinner(storage_path=path)
        assert pinner._pinned == {}

    def test_list_storage_resets_to_empty(self, tmp_path):
        path = str(tmp_path / "pinned.json")
        with open(path, "w") as f:
            f.write("[1, 2, 3]")
        pinner = ContentPinner(storage_path=path)
        assert pinner._pinned == {}

    def test_number_storage_resets_to_empty(self, tmp_path):
        path = str(tmp_path / "pinned.json")
        with open(path, "w") as f:
            f.write("42")
        pinner = ContentPinner(storage_path=path)
        assert pinner._pinned == {}
