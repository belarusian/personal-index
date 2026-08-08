"""Base migration infrastructure for personal-index."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MigrationRecord:
    """Record of an applied migration."""

    version: int
    name: str
    applied_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "applied_at": self.applied_at,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationRecord":
        return cls(**data)


@dataclass
class Migration:
    """Represents a single database migration."""

    version: int
    name: str
    description: str = ""
    up_fn: Optional[Callable] = None
    down_fn: Optional[Callable] = None
    checksum: str = ""

    def apply(self, db: Any) -> bool:
        """Apply the migration (up direction).

        Args:
            db: Database connection or storage backend.

        Returns:
            True if migration was applied successfully.
        """
        if self.up_fn is None:
            logger.warning("Migration %s has no up function", self.name)
            return False
        logger.info("Applying migration %s (v%d)", self.name, self.version)
        self.up_fn(db)
        return True

    def rollback(self, db: Any) -> bool:
        """Rollback the migration (down direction).

        Args:
            db: Database connection or storage backend.

        Returns:
            True if migration was rolled back successfully.
        """
        if self.down_fn is None:
            logger.warning("Migration %s has no down function", self.name)
            return False
        logger.info("Rolling back migration %s (v%d)", self.name, self.version)
        self.down_fn(db)
        return True


class MigrationManager:
    """Manages database migrations."""

    def __init__(
        self,
        db: Any,
        migrations_dir: Optional[str] = None,
        state_file: Optional[str] = None,
    ):
        self.db = db
        self.migrations_dir = Path(migrations_dir) if migrations_dir else Path(
            os.path.dirname(__file__)
        )
        self.state_file = (
            Path(state_file) if state_file else Path("migrations_state.json")
        )
        self._migrations: List[Migration] = []
        self._applied: Dict[int, MigrationRecord] = {}
        self._load_state()
        self._discover_migrations()

    def _load_state(self):
        """Load migration state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                self._applied = {
                    int(v): MigrationRecord.from_dict(d)
                    for v, d in data.get("applied", {}).items()
                }
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to load migration state: %s", e)
                self._applied = {}
        else:
            self._applied = {}

    def _save_state(self):
        """Save migration state to disk."""
        data = {
            "applied": {
                str(k): v.to_dict() for k, v in self._applied.items()
            }
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def _discover_migrations(self):
        """Discover migration files in the migrations directory."""
        if not self.migrations_dir.exists():
            logger.warning("Migrations directory not found: %s", self.migrations_dir)
            return

        for filepath in sorted(self.migrations_dir.glob("*.py")):
            if filepath.name.startswith("__"):
                continue
            if filepath.name == "base.py":
                continue
            self._load_migration_file(filepath)

    def _load_migration_file(self, filepath: Path):
        """Load a migration from a Python file."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            f"migration_{filepath.stem}", filepath
        )
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error("Failed to load migration %s: %s", filepath.name, e)
            return

        if hasattr(module, "version") and hasattr(module, "name"):
            migration = Migration(
                version=module.version,
                name=module.name,
                description=getattr(module, "description", ""),
                up_fn=getattr(module, "up", None),
                down_fn=getattr(module, "down", None),
            )
            self._migrations.append(migration)

    def get_pending(self) -> List[Migration]:
        """Get list of pending (not yet applied) migrations."""
        applied_versions = set(self._applied.keys())
        return [
            m for m in self._migrations
            if m.version not in applied_versions
        ]

    def get_applied(self) -> List[MigrationRecord]:
        """Get list of applied migrations."""
        return sorted(self._applied.values(), key=lambda r: r.version)

    def migrate(self, target: Optional[int] = None) -> List[MigrationRecord]:
        """Apply pending migrations up to target version.

        Args:
            target: Target version. If None, apply all pending.

        Returns:
            List of newly applied migration records.
        """
        pending = self.get_pending()
        applied = []

        for migration in pending:
            if target is not None and migration.version > target:
                break
            if migration.apply(self.db):
                record = MigrationRecord(
                    version=migration.version,
                    name=migration.name,
                )
                self._applied[migration.version] = record
                applied.append(record)
                logger.info(
                    "Applied migration v%d: %s", migration.version, migration.name
                )

        self._save_state()
        return applied

    def rollback(self, steps: int = 1) -> List[MigrationRecord]:
        """Rollback applied migrations.

        Args:
            steps: Number of migrations to rollback.

        Returns:
            List of rolled back migration records.
        """
        applied = sorted(self._applied.values(), key=lambda r: r.version, reverse=True)
        rolled_back = []

        for record in applied[:steps]:
            migration = next(
                (m for m in self._migrations if m.version == record.version),
                None,
            )
            if migration and migration.rollback(self.db):
                del self._applied[record.version]
                rolled_back.append(record)
                logger.info(
                    "Rolled back migration v%d: %s",
                    record.version,
                    record.name,
                )

        self._save_state()
        return rolled_back

    def status(self) -> Dict[str, Any]:
        """Get migration status summary."""
        applied = self.get_applied()
        pending = self.get_pending()
        return {
            "applied": [r.to_dict() for r in applied],
            "pending": [
                {"version": m.version, "name": m.name, "description": m.description}
                for m in pending
            ],
            "total_applied": len(applied),
            "total_pending": len(pending),
            "latest_version": applied[-1].version if applied else 0,
        }
