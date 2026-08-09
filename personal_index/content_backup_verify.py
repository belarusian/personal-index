"""Content backup verify module - Backup verification and integrity checking."""

from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ChecksumAlgorithm(str, Enum):
    """Supported checksum algorithms for backup verification."""

    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class BackupStatus(str, Enum):
    """Status of a backup verification."""

    PENDING = "pending"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    CORRUPTED = "corrupted"


@dataclass
class BackupManifest:
    """Manifest file describing backup contents and checksums."""

    backup_id: str
    algorithm: ChecksumAlgorithm
    files: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    description: str = ""

    def add_file(self, path: str, checksum: str, size: int) -> None:
        """Add a file entry to the manifest.

        Args:
            path: File path within the backup.
            checksum: Expected checksum of the file.
            size: File size in bytes.
        """
        self.files.append({
            "path": path,
            "checksum": checksum,
            "size": size,
            "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

    def get_checksum(self, path: str) -> Optional[str]:
        """Get the expected checksum for a file path.

        Args:
            path: File path to look up.

        Returns:
            Checksum string if found, None otherwise.
        """
        for file_entry in self.files:
            if file_entry["path"] == path:
                return file_entry["checksum"]
        return None

    def total_size(self) -> int:
        """Calculate total size of all files in the manifest.

        Returns:
            Total size in bytes.
        """
        return sum(f["size"] for f in self.files)

    def file_count(self) -> int:
        """Get the number of files in the manifest.

        Returns:
            Number of file entries.
        """
        return len(self.files)


@dataclass
class VerificationResult:
    """Result of a backup verification operation."""

    backup_id: str
    status: BackupStatus
    files_checked: int
    files_passed: int
    errors: list[str] = field(default_factory=list)
    verified_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def is_success(self) -> bool:
        """Check if verification was successful.

        Returns:
            True if status is VERIFIED.
        """
        return self.status == BackupStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "backup_id": self.backup_id,
            "status": self.status.value,
            "files_checked": self.files_checked,
            "files_passed": self.files_passed,
            "errors": self.errors,
            "verified_at": self.verified_at,
        }


class BackupIntegrity:
    """Utilities for computing and verifying backup integrity."""

    @staticmethod
    def compute_checksum(data: str, algorithm: ChecksumAlgorithm) -> str:
        """Compute checksum of data using specified algorithm.

        Args:
            data: Data string to checksum.
            algorithm: Checksum algorithm to use.

        Returns:
            Hex digest of the checksum.
        """
        hash_funcs = {
            ChecksumAlgorithm.MD5: hashlib.md5,
            ChecksumAlgorithm.SHA1: hashlib.sha1,
            ChecksumAlgorithm.SHA256: hashlib.sha256,
            ChecksumAlgorithm.SHA512: hashlib.sha512,
        }
        hasher = hash_funcs[algorithm](data.encode())
        return hasher.hexdigest()

    @staticmethod
    def verify_checksum(
        data: str, expected: str, algorithm: ChecksumAlgorithm
    ) -> bool:
        """Verify data matches expected checksum.

        Args:
            data: Data to verify.
            expected: Expected checksum string.
            algorithm: Algorithm used for the checksum.

        Returns:
            True if checksums match.
        """
        actual = BackupIntegrity.compute_checksum(data, algorithm)
        return actual == expected


class BackupVerifier:
    """Verifies backup integrity against a manifest."""

    def _compute_checksum(self, data: str, algorithm: ChecksumAlgorithm) -> str:
        """Compute checksum using BackupIntegrity.

        Args:
            data: Data to checksum.
            algorithm: Algorithm to use.

        Returns:
            Hex digest string.
        """
        return BackupIntegrity.compute_checksum(data, algorithm)

    def verify_manifest(
        self,
        manifest: BackupManifest,
        file_data: dict[str, str],
    ) -> VerificationResult:
        """Verify all files in a manifest against actual data.

        Args:
            manifest: BackupManifest with expected checksums.
            file_data: Dictionary mapping file paths to their content.

        Returns:
            VerificationResult with outcome.
        """
        errors: list[str] = []
        files_checked = 0
        files_passed = 0

        for file_entry in manifest.files:
            path = file_entry["path"]
            expected_checksum = file_entry["checksum"]
            files_checked += 1

            if path not in file_data:
                errors.append(f"{path}: file missing")
                continue

            actual_checksum = self._compute_checksum(file_data[path], manifest.algorithm)
            if actual_checksum == expected_checksum:
                files_passed += 1
            else:
                errors.append(f"{path}: checksum mismatch (expected: {expected_checksum[:8]}..., got: {actual_checksum[:8]}...)")

        if not manifest.files:
            status = BackupStatus.VERIFIED
        elif files_passed == files_checked and not errors:
            status = BackupStatus.VERIFIED
        elif files_passed > 0:
            # Partial success - some files OK, some failed
            status = BackupStatus.FAILED
        else:
            # All files failed - could be corrupted or just failed
            status = BackupStatus.FAILED

        return VerificationResult(
            backup_id=manifest.backup_id,
            status=status,
            files_checked=files_checked,
            files_passed=files_passed,
            errors=errors,
        )

    def generate_report(self, result: VerificationResult) -> str:
        """Generate a human-readable verification report.

        Args:
            result: VerificationResult to report on.

        Returns:
            Formatted report string.
        """
        lines = [
            f"Backup Verification Report",
            f"==========================",
            f"Backup ID: {result.backup_id}",
            f"Status: {result.status.value}",
            f"Files checked: {result.files_checked}",
            f"Files passed: {result.files_passed}",
            f"Verified at: {result.verified_at}",
        ]
        if result.errors:
            lines.append(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                lines.append(f"  - {error}")
        return "\n".join(lines)
