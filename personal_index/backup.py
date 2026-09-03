"""Backup and restore system for personal index data."""

from __future__ import annotations

import json
import os
import tarfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class BackupManifest:
    """Manifest describing a backup."""
    backup_id: str = ""
    created_at: str = ""
    source_dir: str = ""
    files: list[str] = field(default_factory=list)
    total_size: int = 0
    file_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.backup_id:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            short_uuid = uuid.uuid4().hex[:6]
            self.backup_id = f"{ts}_{short_uuid}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "backup_id": self.backup_id,
            "created_at": self.created_at,
            "source_dir": self.source_dir,
            "files": self.files,
            "total_size": self.total_size,
            "file_count": self.file_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BackupManifest:
        """Create from dictionary."""
        return cls(**data)


class BackupManager:
    """Manage backups of personal index data."""

    def __init__(self, backup_dir: str | None = None):
        self._backup_dir = backup_dir or str(Path.home() / ".personal_index" / "backups")

    @staticmethod
    def _create_archive(files: list[Path], archive_path: Path, mode: str,
                        source_path: Path) -> None:
        """Create a tar or tar.gz archive from the given files.

        Args:
            files: List of file paths to include in the archive.
            archive_path: Path where the archive will be created.
            mode: Tarfile mode string (e.g. "w" or "w:gz").
            source_path: Source directory for computing relative arcnames.
        """
        with tarfile.open(str(archive_path), mode) as tar:  # type: ignore[call-overload]
            for filepath in files:
                tar.add(str(filepath), arcname=str(filepath.relative_to(source_path)))

    @staticmethod
    def _save_manifest(manifest: BackupManifest, manifest_path: Path) -> None:
        """Save a backup manifest as JSON.

        Args:
            manifest: The manifest to save.
            manifest_path: Path where the JSON file will be written.
        """
        with open(str(manifest_path), "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

    def create_backup(self, source_dir: str,
                      include_patterns: list[str] | None = None,
                      exclude_patterns: list[str] | None = None,
                      compress: bool = True) -> BackupManifest:
        """Create a backup of the source directory."""
        source_path = Path(source_dir)
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        manifest = BackupManifest(source_dir=source_dir)
        backup_path = Path(self._backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        files = self._collect_files(source_path, include_patterns, exclude_patterns)
        self._populate_manifest(manifest, files, source_path)
        archive_path = self._build_archive(manifest, files, backup_path, source_path, compress)
        manifest_path = backup_path / f"backup_{manifest.backup_id}.json"
        self._save_manifest(manifest, manifest_path)
        manifest.metadata["archive_path"] = str(archive_path.resolve())
        manifest.metadata["compressed"] = compress
        self._save_manifest(manifest, manifest_path)
        return manifest

    def _populate_manifest(
        self, manifest: BackupManifest, files: list[Path], source: Path
    ) -> None:
        """Set file list and total size on manifest."""
        manifest.files = [str(f.relative_to(source)) for f in files]
        manifest.file_count = len(files)
        manifest.total_size = sum(f.stat().st_size for f in files)

    def _build_archive(
        self, manifest: BackupManifest, files: list[Path],
        backup_path: Path, source: Path, compress: bool
    ) -> Path:
        """Create archive and return its path."""
        if compress:
            name, mode = f"backup_{manifest.backup_id}.tar.gz", "w:gz"
        else:
            name, mode = f"backup_{manifest.backup_id}.tar", "w"
        archive_path = backup_path / name
        self._create_archive(files, archive_path, mode, source)
        return archive_path

    def list_backups(self) -> list[BackupManifest]:
        """List all available backups."""
        backup_path = Path(self._backup_dir)
        if not backup_path.exists():
            return []

        manifests = []
        for manifest_file in sorted(backup_path.glob("backup_*.json")):
            try:
                with open(str(manifest_file)) as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                manifests.append(BackupManifest.from_dict(data))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        return manifests

    def restore_backup(self, backup_id: str, target_dir: str) -> dict[str, object]:
        """Restore a backup to the target directory."""
        backup_path = Path(self._backup_dir)
        manifest_file = backup_path / f"backup_{backup_id}.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Backup not found: {backup_id}")
        with open(str(manifest_file)) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(
                f"Invalid manifest in {manifest_file}: "
                f"expected dict, got {type(data).__name__}"
            )
        try:
            manifest = BackupManifest.from_dict(data)
        except (KeyError, TypeError):
            raise ValueError(
                f"Invalid manifest in {manifest_file}: "
                f"unexpected or missing keys in dict manifest"
            ) from None
        archive_path = self._find_archive(manifest, backup_path, backup_id)
        mode = "r:gz" if str(archive_path).endswith(".tar.gz") else "r"
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        restored = self._extract_archive(archive_path, mode, target)
        return {
            "backup_id": backup_id,
            "target_dir": str(target),
            "files_restored": restored,
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }

    def _find_archive(
        self, manifest: BackupManifest, backup_path: Path, backup_id: str
    ) -> Path:
        """Locate the archive file for a backup."""
        archive_path = Path(manifest.metadata.get("archive_path", ""))
        if not archive_path.exists() or not archive_path.is_file():
            archive_path = backup_path / f"backup_{backup_id}.tar.gz"
            if not archive_path.exists() or not archive_path.is_file():
                archive_path = backup_path / f"backup_{backup_id}.tar"
        if not archive_path.exists() or not archive_path.is_file():
            raise FileNotFoundError(f"Archive not found for backup: {backup_id}")
        return archive_path

    @staticmethod
    def _extract_archive(archive_path: Path, mode: str, target: Path) -> int:
        """Extract archive and return number of files restored."""
        with tarfile.open(str(archive_path), mode) as tar:  # type: ignore[call-overload]
            count = len(tar.getnames())
            tar.extractall(path=str(target), filter="data")
        return count

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup and its archive."""
        backup_path = Path(self._backup_dir)
        manifest_file = backup_path / f"backup_{backup_id}.json"

        if not manifest_file.exists():
            return False

        # Delete archives
        for archive_name in [f"backup_{backup_id}.tar.gz", f"backup_{backup_id}.tar"]:
            archive_path = backup_path / archive_name
            if archive_path.exists():
                archive_path.unlink()

        # Delete manifest
        manifest_file.unlink()
        return True

    def get_backup_info(self, backup_id: str) -> BackupManifest | None:
        """Get info about a specific backup."""
        backup_path = Path(self._backup_dir)
        manifest_file = backup_path / f"backup_{backup_id}.json"

        if not manifest_file.exists():
            return None

        with open(str(manifest_file)) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        try:
            return BackupManifest.from_dict(data)
        except (KeyError, TypeError):
            return None

    def get_total_backup_size(self) -> int:
        """Get total size of all backups."""
        backup_path = Path(self._backup_dir)
        if not backup_path.exists():
            return 0

        total = 0
        for archive in backup_path.glob("backup_*.tar*"):
            total += archive.stat().st_size
        return total

    def cleanup_old_backups(self, keep: int = 5) -> list[str]:
        """Keep only the N most recent backups. Returns deleted backup IDs."""
        backups = self.list_backups()
        deleted = []

        if len(backups) > keep:
            to_delete = backups[:-keep]
            for backup in to_delete:
                if self.delete_backup(backup.backup_id):
                    deleted.append(backup.backup_id)

        return deleted

    def _collect_files(self, source: Path,
                       include: list[str] | None = None,
                       exclude: list[str] | None = None) -> list[Path]:
        """Collect files from source directory with filtering."""
        files = []
        exclude = exclude or []

        for root, dirs, filenames in os.walk(source):
            # Skip hidden directories and common non-data dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                       {"__pycache__", ".git", ".pytest_cache", ".mypy_cache",
                        "*.egg-info", "node_modules"}]

            for filename in filenames:
                filepath = Path(root) / filename

                # Check exclude patterns
                if any(filepath.match(p) for p in exclude):
                    continue

                # Check include patterns
                if include and not any(filepath.match(p) for p in include):
                    continue

                files.append(filepath)

        return files
