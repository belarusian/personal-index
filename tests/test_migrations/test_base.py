"""Tests for migration base module."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from personal_index.migrations.base import (
    Migration,
    MigrationManager,
    MigrationRecord,
)


class TestMigrationRecord:
    """Tests for MigrationRecord."""

    def test_to_dict(self):
        """Test serialization to dict."""
        record = MigrationRecord(version=1, name="test")
        d = record.to_dict()
        assert d["version"] == 1
        assert d["name"] == "test"
        assert "applied_at" in d

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "version": 2,
            "name": "test_migration",
            "applied_at": "2024-01-01T00:00:00",
            "checksum": "abc123",
        }
        record = MigrationRecord.from_dict(data)
        assert record.version == 2
        assert record.name == "test_migration"
        assert record.checksum == "abc123"


class TestMigration:
    """Tests for Migration class."""

    def test_apply_calls_up_fn(self):
        """Test that apply calls the up function."""
        called = []

        def up_fn(db):
            called.append("up")

        migration = Migration(version=1, name="test", up_fn=up_fn)
        result = migration.apply("fake_db")
        assert result is True
        assert called == ["up"]

    def test_apply_no_up_fn(self):
        """Test apply with no up function."""
        migration = Migration(version=1, name="test")
        result = migration.apply("fake_db")
        assert result is False

    def test_rollback_calls_down_fn(self):
        """Test that rollback calls the down function."""
        called = []

        def down_fn(db):
            called.append("down")

        migration = Migration(version=1, name="test", down_fn=down_fn)
        result = migration.rollback("fake_db")
        assert result is True
        assert called == ["down"]

    def test_rollback_no_down_fn(self):
        """Test rollback with no down function."""
        migration = Migration(version=1, name="test")
        result = migration.rollback("fake_db")
        assert result is False


class TestMigrationManager:
    """Tests for MigrationManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for migration state."""
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return MagicMock()

    @pytest.fixture
    def manager(self, temp_dir, mock_db):
        """Create a migration manager."""
        return MigrationManager(
            db=mock_db,
            migrations_dir=temp_dir,
            state_file=os.path.join(temp_dir, "state.json"),
        )

    def test_get_pending_empty(self, manager):
        """Test pending migrations when none exist."""
        assert manager.get_pending() == []

    def test_get_applied_empty(self, manager):
        """Test applied migrations when none exist."""
        assert manager.get_applied() == []

    def test_status_empty(self, manager):
        """Test status when no migrations."""
        status = manager.status()
        assert status["total_applied"] == 0
        assert status["total_pending"] == 0
        assert status["latest_version"] == 0

    def test_migrate_no_pending(self, manager):
        """Test migrate with no pending migrations."""
        applied = manager.migrate()
        assert applied == []

    def test_state_persistence(self, temp_dir, mock_db):
        """Test that migration state is persisted."""
        state_file = os.path.join(temp_dir, "state.json")
        mgr = MigrationManager(
            db=mock_db,
            migrations_dir=temp_dir,
            state_file=state_file,
        )

        # Manually add an applied migration
        mgr._applied[1] = MigrationRecord(version=1, name="test")
        mgr._save_state()

        # Load new manager and verify state
        mgr2 = MigrationManager(
            db=mock_db,
            migrations_dir=temp_dir,
            state_file=state_file,
        )
        assert 1 in mgr2._applied
        assert mgr2._applied[1].name == "test"

    def test_rollback_no_applied(self, manager):
        """Test rollback with no applied migrations."""
        rolled_back = manager.rollback()
        assert rolled_back == []

    def test_discover_migrations(self, temp_dir, mock_db):
        """Test migration discovery from directory."""
        # Create a migration file
        migration_file = os.path.join(temp_dir, "001_test.py")
        with open(migration_file, "w") as f:
            f.write("version = 1\nname = 'test'\n")

        mgr = MigrationManager(
            db=mock_db,
            migrations_dir=temp_dir,
            state_file=os.path.join(temp_dir, "state.json"),
        )
        pending = mgr.get_pending()
        assert len(pending) == 1
        assert pending[0].version == 1
        assert pending[0].name == "test"

    def test_migrate_applies_pending(self, temp_dir, mock_db):
        """Test that migrate applies pending migrations."""
        migration_file = os.path.join(temp_dir, "001_test.py")
        with open(migration_file, "w") as f:
            f.write(
                "version = 1\nname = 'test'\n"
                "def up(db): db.up_called = True\n"
            )

        mgr = MigrationManager(
            db=mock_db,
            migrations_dir=temp_dir,
            state_file=os.path.join(temp_dir, "state.json"),
        )
        applied = mgr.migrate()
        assert len(applied) == 1
        assert applied[0].version == 1
        assert mock_db.up_called is True
