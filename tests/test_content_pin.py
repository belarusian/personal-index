"""Tests for content_pin module."""

from __future__ import annotations

import pytest
from personal_index.content_pin import (
    PinManager,
    PinnedVersion,
    PinError,
)


class TestPinnedVersion:
    def test_create_pinned_version(self):
        pinned = PinnedVersion(
            content_id="doc-1",
            version_number=2,
            pinned_by="user1",
            reason="Important reference",
        )
        assert pinned.content_id == "doc-1"
        assert pinned.version_number == 2
        assert pinned.pinned_by == "user1"
        assert pinned.reason == "Important reference"

    def test_pinned_version_to_dict(self):
        pinned = PinnedVersion(
            content_id="doc-1",
            version_number=1,
            pinned_by="admin",
            reason="Baseline",
        )
        d = pinned.to_dict()
        assert d["content_id"] == "doc-1"
        assert d["version_number"] == 1
        assert d["pinned_by"] == "admin"


class TestPinError:
    def test_pin_error_message(self):
        err = PinError("Cannot pin")
        assert str(err) == "Cannot pin"

    def test_pin_error_with_content_id(self):
        err = PinError("Version not found", content_id="doc-1")
        assert "doc-1" in str(err)


class TestPinManager:
    def test_create_manager(self):
        manager = PinManager()
        assert manager.max_pins_per_content == 10

    def test_pin_no_versions(self):
        manager = PinManager()
        with pytest.raises(PinError):
            manager.pin("doc-1", 1)

    def test_pin_valid_version(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        result = manager.pin("doc-1", 1)
        assert result is not None
        assert result.content_id == "doc-1"
        assert result.version_number == 1

    def test_pin_with_reason(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        result = manager.pin("doc-1", 1, reason="Important baseline")
        assert result.reason == "Important baseline"

    def test_pin_with_pinned_by(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        result = manager.pin("doc-1", 1, pinned_by="admin")
        assert result.pinned_by == "admin"

    def test_pin_nonexistent_version(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        with pytest.raises(PinError):
            manager.pin("doc-1", 99)

    def test_pin_already_pinned(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.pin("doc-1", 1)
        with pytest.raises(PinError):
            manager.pin("doc-1", 1)

    def test_pin_multiple_versions(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        manager.pin("doc-1", 1)
        manager.pin("doc-1", 3)
        pins = manager.get_pins("doc-1")
        assert len(pins) == 2

    def test_unpin(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.pin("doc-1", 1)
        manager.unpin("doc-1", 1)
        pins = manager.get_pins("doc-1")
        assert len(pins) == 0

    def test_unpin_nonexistent(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.pin("doc-1", 1)
        with pytest.raises(PinError):
            manager.unpin("doc-1", 2)

    def test_get_pins(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.pin("doc-1", 1)
        pins = manager.get_pins("doc-1")
        assert len(pins) == 1
        assert pins[0].version_number == 1

    def test_get_pins_empty(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        pins = manager.get_pins("doc-1")
        assert len(pins) == 0

    def test_is_pinned(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.pin("doc-1", 1)
        assert manager.is_pinned("doc-1", 1) is True
        assert manager.is_pinned("doc-1", 2) is False

    def test_max_pins_enforced(self):
        manager = PinManager(max_pins_per_content=2)
        for i in range(5):
            manager.save_version("doc-1", f"V{i+1}")
        manager.pin("doc-1", 1)
        manager.pin("doc-1", 2)
        with pytest.raises(PinError):
            manager.pin("doc-1", 3)

    def test_pins_preserved_after_rollback(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        manager.pin("doc-1", 1)
        manager.rollback("doc-1", 1)
        pins = manager.get_pins("doc-1")
        assert len(pins) == 1

    def test_get_all_pins(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-2", "V1")
        manager.pin("doc-1", 1)
        manager.pin("doc-2", 1)
        all_pins = manager.get_all_pins()
        assert len(all_pins) == 2

    def test_pin_count(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.pin("doc-1", 1)
        assert manager.pin_count("doc-1") == 1

    def test_pin_version_content(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.pin("doc-1", 1)
        content = manager.get_pinned_content("doc-1", 1)
        assert content == "V1"

    def test_unpin_all(self):
        manager = PinManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.pin("doc-1", 1)
        manager.pin("doc-1", 2)
        manager.unpin_all("doc-1")
        assert len(manager.get_pins("doc-1")) == 0
