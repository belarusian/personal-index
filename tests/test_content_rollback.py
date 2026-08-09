"""Tests for content_rollback module."""

from __future__ import annotations

import pytest
from personal_index.content_rollback import (
    RollbackManager,
    RollbackRecord,
    RollbackError,
)


class TestRollbackRecord:
    def test_create_rollback_record(self):
        record = RollbackRecord(
            content_id="doc-1",
            from_version=3,
            to_version=1,
            reason="Fix typo",
        )
        assert record.content_id == "doc-1"
        assert record.from_version == 3
        assert record.to_version == 1
        assert record.reason == "Fix typo"

    def test_rollback_record_to_dict(self):
        record = RollbackRecord(
            content_id="doc-1",
            from_version=3,
            to_version=1,
            reason="Fix typo",
        )
        d = record.to_dict()
        assert d["content_id"] == "doc-1"
        assert d["from_version"] == 3
        assert d["to_version"] == 1


class TestRollbackError:
    def test_rollback_error_message(self):
        err = RollbackError("Cannot rollback")
        assert str(err) == "Cannot rollback"

    def test_rollback_error_with_content_id(self):
        err = RollbackError("Invalid version", content_id="doc-1")
        assert "doc-1" in str(err)


class TestRollbackManager:
    def test_create_manager(self):
        manager = RollbackManager()
        assert manager.max_rollback_history == 50

    def test_rollback_no_versions(self):
        manager = RollbackManager()
        with pytest.raises(RollbackError):
            manager.rollback("doc-1", 1)

    def test_rollback_to_current_version(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        result = manager.rollback("doc-1", 2)
        assert result is None  # Already at target version

    def test_rollback_to_previous_version(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        result = manager.rollback("doc-1", 1)
        assert result is not None
        assert result.from_version == 3
        assert result.to_version == 1

    def test_rollback_to_nonexistent_version(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        with pytest.raises(RollbackError):
            manager.rollback("doc-1", 99)

    def test_rollback_preserves_history(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        manager.rollback("doc-1", 1)
        versions = manager.get_versions("doc-1")
        # After rollback, V1 content should be current but history preserved
        assert len(versions) >= 2

    def test_rollback_creates_new_version(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        manager.rollback("doc-1", 1)
        latest = manager.get_latest("doc-1")
        assert latest.content == "V1"

    def test_rollback_with_reason(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        result = manager.rollback("doc-1", 1, reason="Revert bad change")
        assert result.reason == "Revert bad change"

    def test_rollback_history(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        manager.rollback("doc-1", 1)
        history = manager.get_rollback_history("doc-1")
        assert len(history) >= 1

    def test_rollback_multiple_content_ids(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "A1")
        manager.save_version("doc-1", "A2")
        manager.save_version("doc-2", "B1")
        manager.save_version("doc-2", "B2")
        manager.rollback("doc-1", 1)
        latest = manager.get_latest("doc-1")
        assert latest.content == "A1"
        # doc-2 should be unaffected
        latest2 = manager.get_latest("doc-2")
        assert latest2.content == "B2"

    def test_rollback_to_version_zero(self):
        """Version 0 means rollback to the very first version (v1)."""
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        result = manager.rollback("doc-1", 0)
        assert result is not None
        assert result.to_version == 1  # v0 maps to first version which is v1

    def test_rollback_chain(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        manager.save_version("doc-1", "V4")
        manager.rollback("doc-1", 2)
        latest = manager.get_latest("doc-1")
        assert latest.content == "V2"

    def test_rollback_max_history(self):
        manager = RollbackManager(max_rollback_history=3)
        manager.save_version("doc-1", "V1")
        for i in range(10):
            manager.save_version("doc-1", f"V{i+2}")
            manager.rollback("doc-1", 1)
        history = manager.get_rollback_history("doc-1")
        assert len(history) <= 3

    def test_rollback_get_available_versions(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        available = manager.get_available_versions("doc-1")
        assert len(available) == 3

    def test_rollback_can_rollback(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        assert manager.can_rollback("doc-1") is True
        assert manager.can_rollback("nonexistent") is False

    def test_rollback_rollback_to_latest(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        result = manager.rollback("doc-1", 2)
        assert result is None

    def test_rollback_version_number_after_rollback(self):
        manager = RollbackManager()
        manager.save_version("doc-1", "V1")
        manager.save_version("doc-1", "V2")
        manager.save_version("doc-1", "V3")
        manager.rollback("doc-1", 1)
        latest = manager.get_latest("doc-1")
        assert latest.version_number > 3  # New version created
