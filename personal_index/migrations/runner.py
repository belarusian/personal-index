"""Migration runner for executing and rolling back migrations."""

from __future__ import annotations

import logging
import time

from personal_index.migrations.base import (
    MigrationRecord,
    MigrationRegistry,
    MigrationStatus,
    MigrationStore,
)

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Runs migrations against a migration store."""

    def __init__(
        self,
        registry: MigrationRegistry | None = None,
        store: MigrationStore | None = None,
    ):
        self.registry = registry or MigrationRegistry()
        self.store = store or MigrationStore()

    def run_pending(self, dry_run: bool = False) -> list[MigrationRecord]:
        """Run all pending migrations.

        Args:
            dry_run: If True, only validate without applying.

        Returns:
            List of MigrationRecord for applied migrations.
        """
        pending = self.registry.get_pending(self.store.get_applied_versions())
        results = []

        for migration_class in pending:
            migration = migration_class()
            errors = migration.validate()
            if errors:
                logger.warning(
                    "Migration %s validation failed: %s",
                    migration.name,
                    errors,
                )
                raise MigrationError(
                    f"Migration {migration.name} validation failed: {errors}"
                )

            if dry_run:
                logger.info("[DRY RUN] Would apply migration: %s", migration.name)
                continue

            start = time.monotonic()
            operations = migration.upgrade()
            duration_ms = (time.monotonic() - start) * 1000

            record = self.store.record_applied(migration, duration_ms)
            results.append(record)
            logger.info(
                "Applied migration %s (v%d) in %.1fms: %s",
                migration.name,
                migration.version,
                duration_ms,
                operations,
            )

        return results

    def rollback(self, steps: int = 1, dry_run: bool = False) -> list[MigrationRecord]:
        """Rollback applied migrations.

        Args:
            steps: Number of migrations to rollback.
            dry_run: If True, only validate without rolling back.

        Returns:
            List of MigrationRecord for rolled back migrations.
        """
        applied = self.registry.get_applied(self.store.get_applied_versions())
        to_rollback = list(reversed(applied))[:steps]
        results = []

        for migration_class in to_rollback:
            migration = migration_class()

            if dry_run:
                logger.info("[DRY RUN] Would rollback migration: %s", migration.name)
                continue

            start = time.monotonic()
            operations = migration.downgrade()
            duration_ms = (time.monotonic() - start) * 1000

            self.store.remove_record(migration.version)
            record = MigrationRecord(
                name=migration.name,
                version=migration.version,
                duration_ms=duration_ms,
            )
            results.append(record)
            logger.info(
                "Rolled back migration %s (v%d) in %.1fms: %s",
                migration.name,
                migration.version,
                duration_ms,
                operations,
            )

        return results

    def get_status(self) -> MigrationStatus:
        """Get current migration status."""
        applied_versions = self.store.get_applied_versions()
        all_versions = self.registry.get_all_versions()
        pending_versions = [v for v in all_versions if v not in applied_versions]

        applied_names = []
        for v in applied_versions:
            record = self.store.get_record(v)
            if record:
                applied_names.append(record.name)

        pending_names = []
        for v in pending_versions:
            cls = self.registry.get_migration(v)
            if cls:
                pending_names.append(cls().name)

        return MigrationStatus(
            current_version=self.store.get_current_version(),
            total_migrations=len(all_versions),
            pending=pending_names,
            applied=applied_names,
            is_up_to_date=len(pending_versions) == 0,
        )

    def validate_all(self) -> list[str]:
        """Validate all pending migrations without applying.

        Returns:
            List of validation errors (empty if all valid).
        """
        errors: list[str] = []
        pending = self.registry.get_pending(self.store.get_applied_versions())
        for migration_class in pending:
            migration = migration_class()
            migration_errors = migration.validate()
            if migration_errors:
                errors.extend(
                    f"{migration.name}: {err}" for err in migration_errors
                )
        return errors


class MigrationError(Exception):
    """Error during migration execution."""
