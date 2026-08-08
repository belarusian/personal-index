"""Tests for migration runner."""

from __future__ import annotations

import pytest

from personal_index.migrations.base import (
    BaseMigration,
    MigrationRegistry,
    MigrationStore,
)
from personal_index.migrations.runner import (
    MigrationError,
    MigrationRunner,
)


class TestMigration1(BaseMigration):
    version = 1
    name = "001_create_users"
    description = "Create users table"

    def upgrade(self):
        return ["CREATE TABLE users"]

    def downgrade(self):
        return ["DROP TABLE users"]


class TestMigration2(BaseMigration):
    version = 2
    name = "002_create_posts"
    description = "Create posts table"

    def upgrade(self):
        return ["CREATE TABLE posts"]

    def downgrade(self):
        return ["DROP TABLE posts"]


class TestMigration3(BaseMigration):
    version = 3
    name = "003_add_index"
    description = "Add index on posts"

    def upgrade(self):
        return ["CREATE INDEX idx_posts_title ON posts(title)"]

    def downgrade(self):
        return ["DROP INDEX idx_posts_title"]


class TestMigrationWithValidation(BaseMigration):
    version = 4
    name = "004_failing_validation"
    description = "Migration that fails validation"

    def upgrade(self):
        return ["ALTER TABLE"]

    def downgrade(self):
        return ["ALTER TABLE"]

    def validate(self):
        return ["Required table does not exist"]


@pytest.fixture
def registry():
    registry = MigrationRegistry()
    registry.register(TestMigration1)
    registry.register(TestMigration2)
    registry.register(TestMigration3)
    return registry


@pytest.fixture
def store(tmp_path):
    return MigrationStore(store_path=str(tmp_path / "migrations.json"))


@pytest.fixture
def runner(registry, store):
    return MigrationRunner(registry=registry, store=store)


class TestMigrationRunner:
    def test_run_pending_all(self, runner):
        results = runner.run_pending()
        assert len(results) == 3
        assert results[0].version == 1
        assert results[1].version == 2
        assert results[2].version == 3

    def test_run_pending_dry_run(self, runner):
        results = runner.run_pending(dry_run=True)
        assert len(results) == 0
        assert runner.store.get_applied_versions() == []

    def test_run_pending_no_pending(self, runner):
        runner.run_pending()
        results = runner.run_pending()
        assert len(results) == 0

    def test_run_pending_partial(self, runner):
        runner.run_pending()
        # Rollback last one
        runner.rollback(steps=1)
        results = runner.run_pending()
        assert len(results) == 1
        assert results[0].version == 3

    def test_rollback_one_step(self, runner):
        runner.run_pending()
        results = runner.rollback(steps=1)
        assert len(results) == 1
        assert results[0].version == 3
        assert 3 not in runner.store.get_applied_versions()

    def test_rollback_multiple_steps(self, runner):
        runner.run_pending()
        results = runner.rollback(steps=2)
        assert len(results) == 2
        assert results[0].version == 3
        assert results[1].version == 2
        assert runner.store.get_applied_versions() == [1]

    def test_rollback_dry_run(self, runner):
        runner.run_pending()
        results = runner.rollback(steps=1, dry_run=True)
        assert len(results) == 0
        assert 3 in runner.store.get_applied_versions()

    def test_rollback_no_applied(self, runner):
        results = runner.rollback(steps=1)
        assert len(results) == 0

    def test_rollback_more_than_applied(self, runner):
        runner.run_pending()
        results = runner.rollback(steps=10)
        assert len(results) == 3


class TestMigrationStatus:
    def test_status_initial(self, runner):
        status = runner.get_status()
        assert status.current_version == 0
        assert status.total_migrations == 3
        assert status.is_up_to_date is False
        assert len(status.pending) == 3

    def test_status_after_run(self, runner):
        runner.run_pending()
        status = runner.get_status()
        assert status.current_version == 3
        assert status.is_up_to_date is True
        assert len(status.pending) == 0
        assert len(status.applied) == 3

    def test_status_after_rollback(self, runner):
        runner.run_pending()
        runner.rollback(steps=1)
        status = runner.get_status()
        assert status.current_version == 2
        assert status.is_up_to_date is False
        assert len(status.pending) == 1


class TestValidateAll:
    def test_validate_all_pass(self, runner):
        errors = runner.validate_all()
        assert errors == []

    def test_validate_all_fail(self, registry, store):
        registry.register(TestMigrationWithValidation)
        runner = MigrationRunner(registry=registry, store=store)
        errors = runner.validate_all()
        assert len(errors) > 0
        assert "Required table does not exist" in errors[0]


class TestMigrationError:
    def test_run_with_failing_validation(self, registry, store):
        registry.register(TestMigrationWithValidation)
        runner = MigrationRunner(registry=registry, store=store)
        with pytest.raises(MigrationError, match="validation failed"):
            runner.run_pending()
