"""Tests for migration base classes."""

from __future__ import annotations

import pytest

from personal_index.migrations.base import (
    BaseMigration,
    MigrationRecord,
    MigrationRegistry,
    MigrationStatus,
    MigrationStore,
)


class SampleMigration(BaseMigration):
    version = 1
    name = "001_sample"
    description = "Sample migration"

    def upgrade(self):
        return ["CREATE TABLE test"]

    def downgrade(self):
        return ["DROP TABLE test"]


class SampleMigration2(BaseMigration):
    version = 2
    name = "002_sample2"
    description = "Second sample migration"

    def upgrade(self):
        return ["ALTER TABLE test ADD COLUMN foo"]

    def downgrade(self):
        return ["ALTER TABLE test DROP COLUMN foo"]


class TestMigrationRecord:
    def test_create_record(self):
        record = MigrationRecord(name="test", version=1)
        assert record.name == "test"
        assert record.version == 1
        assert record.duration_ms == 0.0

    def test_to_dict(self):
        record = MigrationRecord(name="test", version=1, duration_ms=5.5)
        data = record.to_dict()
        assert data["name"] == "test"
        assert data["duration_ms"] == 5.5


class TestMigrationStatus:
    def test_status(self):
        status = MigrationStatus(
            current_version=1, total_migrations=3,
            pending=["002", "003"], applied=["001"],
            is_up_to_date=False,
        )
        assert status.is_up_to_date is False
        assert len(status.pending) == 2

    def test_to_dict(self):
        status = MigrationStatus(
            current_version=2, total_migrations=2,
            pending=[], applied=["001", "002"],
            is_up_to_date=True,
        )
        data = status.to_dict()
        assert data["is_up_to_date"] is True
        assert data["current_version"] == 2


class TestBaseMigration:
    def test_module_name(self):
        m = SampleMigration()
        assert m.module_name == "001_sample"

    def test_validate_empty(self):
        m = SampleMigration()
        assert m.validate() == []

    def test_custom_validate(self):
        class ValidatingMigration(BaseMigration):
            version = 99
            name = "099_validate"

            def upgrade(self):
                return []

            def downgrade(self):
                return []

            def validate(self):
                return ["Table already exists"]

        m = ValidatingMigration()
        errors = m.validate()
        assert len(errors) == 1


class TestMigrationRegistry:
    def test_register(self):
        registry = MigrationRegistry()
        registry.register(SampleMigration)
        assert registry.get_migration(1) is SampleMigration

    def test_get_all_versions(self):
        registry = MigrationRegistry()
        registry.register(SampleMigration)
        registry.register(SampleMigration2)
        assert registry.get_all_versions() == [1, 2]

    def test_get_pending(self):
        registry = MigrationRegistry()
        registry.register(SampleMigration)
        registry.register(SampleMigration2)
        pending = registry.get_pending([1])
        assert len(pending) == 1
        assert pending[0].version == 2

    def test_get_applied(self):
        registry = MigrationRegistry()
        registry.register(SampleMigration)
        registry.register(SampleMigration2)
        applied = registry.get_applied([1, 2])
        assert len(applied) == 2

    def test_no_migration_dir(self):
        registry = MigrationRegistry(migration_dir="/nonexistent")
        assert registry.get_all_versions() == []


class TestMigrationStore:
    def test_record_applied(self, tmp_path):
        store = MigrationStore(store_path=str(tmp_path / "migrations.json"))
        migration = SampleMigration()
        record = store.record_applied(migration, duration_ms=10.0)
        assert record.version == 1
        assert record.duration_ms == 10.0

    def test_get_applied_versions(self, tmp_path):
        store = MigrationStore(store_path=str(tmp_path / "migrations.json"))
        store.record_applied(SampleMigration())
        store.record_applied(SampleMigration2())
        assert store.get_applied_versions() == [1, 2]

    def test_get_current_version(self, tmp_path):
        store = MigrationStore(store_path=str(tmp_path / "migrations.json"))
        assert store.get_current_version() == 0
        store.record_applied(SampleMigration())
        assert store.get_current_version() == 1

    def test_remove_record(self, tmp_path):
        store = MigrationStore(store_path=str(tmp_path / "migrations.json"))
        store.record_applied(SampleMigration())
        assert store.remove_record(1) is True
        assert 1 not in store.get_applied_versions()

    def test_remove_nonexistent_record(self, tmp_path):
        store = MigrationStore(store_path=str(tmp_path / "migrations.json"))
        assert store.remove_record(99) is False

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "migrations.json")
        store1 = MigrationStore(store_path=path)
        store1.record_applied(SampleMigration())
        store2 = MigrationStore(store_path=path)
        assert 1 in store2.get_applied_versions()

    def test_load_corrupted_file(self, tmp_path, caplog):
        path = str(tmp_path / "migrations.json")
        with open(path, "w") as f:
            f.write("not json")
        store = MigrationStore(store_path=path)
        assert store.get_applied_versions() == []
