"""Backup and restore system for personal index data."""

from __future__ import annotations

import json
import os
import tarfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


@dataclass
class BackupManifest:
    """Manifest describing a backup."""
    backup_id: str = ""
    created_at: str = ""
    source_dir: str = ""
    files: List[str] = field(default_factory=list)
    total_size: int = 0
    file_count: int = 0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.backup_id:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            short_uuid = uuid.uuid4().hex[:6]
            self.backup_id = f"{ts}_{short_uuid}"

    def to_dict(self) -> Dict:
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
    def from_dict(cls, data: Dict) -> BackupManifest:
        """Create from dictionary."""
        return cls(**data)


class BackupManager:
    """Manage backups of personal index data."""

    def __init__(self, backup_dir: str | None = None):
        self._backup_dir = backup_dir or str(Path.home() / ".personal_index" / "backups")

    def create_backup(self, source_dir: str,
                      include_patterns: List[str] | None = None,
                      exclude_patterns: List[str] | None = None,
                      compress: bool = True) -> BackupManifest:
        """Create a backup of the source directory."""
        source_path = Path(source_dir)
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        manifest = BackupManifest(source_dir=source_dir)
        backup_path = Path(self._backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        # Collect files
        files = self._collect_files(
            source_path, include_patterns, exclude_patterns
        )
        manifest.files = [str(f.relative_to(source_path)) for f in files]
        manifest.file_count = len(files)

        # Calculate total size
        manifest.total_size = sum(f.stat().st_size for f in files)

        # Create archive
        if compress:
            archive_name = f"backup_{manifest.backup_id}.tar.gz"
            mode = "w:gz"
        else:
            archive_name = f"backup_{manifest.backup_id}.tar"
            mode = "w"
        archive_path = backup_path / archive_name

        with tarfile.open(str(archive_path), mode) as tar:
            for f in files:
                tar.add(str(f), arcname=str(f.relative_to(source_path)))

        # Save manifest
        manifest_path = backup_path / f"backup_{manifest.backup_id}.json"
        with open(str(manifest_path), "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        manifest.metadata["archive_path"] = str(archive_path.resolve())
        manifest.metadata["compressed"] = compress

        # Re-save manifest with updated metadata
        with open(str(manifest_path), "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        return manifest

    def list_backups(self) -> List[BackupManifest]:
        """List all available backups."""
        backup_path = Path(self._backup_dir)
        if not backup_path.exists():
            return []

        manifests = []
        for manifest_file in sorted(backup_path.glob("backup_*.json")):
            try:
                with open(str(manifest_file)) as f:
                    data = json.load(f)
                manifests.append(BackupManifest.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue

        return manifests

    def restore_backup(self, backup_id: str, target_dir: str) -> Dict[str, int]:
        """Restore a backup to the target directory."""
        backup_path = Path(self._backup_dir)
        manifest_file = backup_path / f"backup_{backup_id}.json"

        if not manifest_file.exists():
            raise FileNotFoundError(f"Backup not found: {backup_id}")

        with open(str(manifest_file)) as f:
            manifest = BackupManifest.from_dict(json.load(f))

        # Find archive
        archive_path = Path(manifest.metadata.get("archive_path", ""))
        if not archive_path.exists() or not archive_path.is_file():
            # Try to find by name in backup directory
            archive_name = f"backup_{backup_id}.tar.gz"
            archive_path = backup_path / archive_name
            if not archive_path.exists() or not archive_path.is_file():
                archive_name = f"backup_{backup_id}.tar"
                archive_path = backup_path / archive_name

        if not archive_path.exists() or not archive_path.is_file():
            raise FileNotFoundError(f"Archive not found for backup: {backup_id}")

        # Determine mode
        is_gzip = str(archive_path).endswith(".tar.gz")
        mode = "r:gz" if is_gzip else "r"

        # Extract
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)

        restored_files = 0
        with tarfile.open(str(archive_path), mode) as tar:
            members = tar.getnames()
            restored_files = len(members)
            tar.extractall(path=str(target), filter="data")

        return {
            "backup_id": backup_id,
            "target_dir": str(target),
            "files_restored": restored_files,
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }

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
            return BackupManifest.from_dict(json.load(f))

    def get_total_backup_size(self) -> int:
        """Get total size of all backups."""
        backup_path = Path(self._backup_dir)
        if not backup_path.exists():
            return 0

        total = 0
        for archive in backup_path.glob("backup_*.tar*"):
            total += archive.stat().st_size
        return total

    def cleanup_old_backups(self, keep: int = 5) -> List[str]:
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
                       include: List[str] | None = None,
                       exclude: List[str] | None = None) -> List[Path]:
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
