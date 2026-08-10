"""Base migration framework for personal-index."""

from __future__ import annotations

import importlib
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Type

logger = logging.getLogger(__name__)


@dataclass
class MigrationRecord:
    """Record of an applied migration."""
    name: str
    version: int
    applied_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: float = 0.0
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "applied_at": self.applied_at,
            "duration_ms": self.duration_ms,
            "checksum": self.checksum,
        }


@dataclass
class MigrationStatus:
    """Current migration status."""
    current_version: int
    total_migrations: int
    pending: List[str]
    applied: List[str]
    is_up_to_date: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_version": self.current_version,
            "total_migrations": self.total_migrations,
            "pending": self.pending,
            "applied": self.applied,
            "is_up_to_date": self.is_up_to_date,
        }


class BaseMigration(ABC):
    """Abstract base class for database migrations."""

    version: int = 0
    name: str = ""
    description: str = ""

    @abstractmethod
    def upgrade(self) -> List[str]:
        """Apply the migration. Returns list of operations performed."""
        ...

    @abstractmethod
    def downgrade(self) -> List[str]:
        """Rollback the migration. Returns list of operations performed."""
        ...

    def validate(self) -> List[str]:
        """Validate the migration can be applied. Returns list of errors."""
        return []

    @property
    def module_name(self) -> str:
        if not self.name:
            self.name = f"{self.version:03d}_{self.__class__.__name__.lower()}"
        return self.name


class MigrationRegistry:
    """Registry that discovers and manages migration classes."""

    def __init__(self, migration_dir: str | None = None):
        self._migrations: Dict[int, Type[BaseMigration]] = {}
        self._migration_dir = migration_dir
        if migration_dir:
            self._discover_migrations(migration_dir)

    def register(self, migration_class: Type[BaseMigration]) -> None:
        """Register a migration class."""
        self._migrations[migration_class.version] = migration_class

    def get_migration(self, version: int) -> Type[BaseMigration] | None:
        """Get a migration class by version."""
        return self._migrations.get(version)

    def get_all_versions(self) -> List[int]:
        """Get all registered migration versions in order."""
        return sorted(self._migrations.keys())

    def get_pending(self, applied_versions: List[int]) -> List[Type[BaseMigration]]:
        """Get migrations that haven't been applied yet."""
        pending = []
        for version in self.get_all_versions():
            if version not in applied_versions:
                cls = self._migrations[version]
                pending.append(cls)
        return pending

    def get_applied(self, applied_versions: List[int]) -> List[Type[BaseMigration]]:
        """Get migrations that have been applied."""
        applied = []
        for version in self.get_all_versions():
            if version in applied_versions:
                cls = self._migrations[version]
                applied.append(cls)
        return applied

    def _discover_migrations(self, migration_dir: str) -> None:
        """Discover migration modules in a directory."""
        path = Path(migration_dir)
        if not path.exists():
            logger.warning("Migration directory not found: %s", migration_dir)
            return

        for filepath in sorted(path.glob("*.py")):
            if filepath.name.startswith("_"):
                continue
            module_name = filepath.stem
            try:
                spec = importlib.util.spec_from_file_location(
                    f"personal_index.migrations.{module_name}",
                    str(filepath),
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseMigration)
                            and attr is not BaseMigration
                        ):
                            self.register(attr)
                            logger.debug("Registered migration: %s (v%d)", attr_name, attr.version)
            except Exception as e:
                logger.error("Failed to load migration %s: %s", filepath.name, e)


class MigrationStore:
    """Stores migration history (in-memory or file-based)."""

    def __init__(self, store_path: str | None = None):
        self._records: Dict[int, MigrationRecord] = {}
        self._store_path = store_path
        if store_path and os.path.exists(store_path):
            self._load(store_path)

    def record_applied(self, migration: BaseMigration, duration_ms: float = 0.0) -> MigrationRecord:
        """Record that a migration was applied."""
        record = MigrationRecord(
            name=migration.name,
            version=migration.version,
            duration_ms=duration_ms,
        )
        self._records[migration.version] = record
        if self._store_path:
            self._save(self._store_path)
        return record

    def get_applied_versions(self) -> List[int]:
        """Get list of applied migration versions."""
        return sorted(self._records.keys())

    def get_record(self, version: int) -> MigrationRecord | None:
        """Get migration record by version."""
        return self._records.get(version)

    def remove_record(self, version: int) -> bool:
        """Remove a migration record (for rollback)."""
        if version in self._records:
            del self._records[version]
            if self._store_path:
                self._save(self._store_path)
            return True
        return False

    def get_current_version(self) -> int:
        """Get the current schema version."""
        versions = self.get_applied_versions()
        return max(versions) if versions else 0

    def _save(self, path: str) -> None:
        """Save migration records to file."""
        data = {
            "migrations": [r.to_dict() for r in self._records.values()],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self, path: str) -> None:
        """Load migration records from file."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for record_data in data.get("migrations", []):
                record = MigrationRecord(**record_data)
                self._records[record.version] = record
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning("Failed to load migration store: %s", e)
