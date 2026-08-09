"""Tests for content_backup_verify module - Backup verification and integrity."""

from __future__ import annotations

import pytest
from personal_index.content_backup_verify import (
    BackupIntegrity,
    BackupManifest,
    BackupStatus,
    BackupVerifier,
    ChecksumAlgorithm,
    VerificationResult,
)


class TestChecksumAlgorithm:
    """Tests for ChecksumAlgorithm enum."""

    def test_algorithm_values(self):
        assert ChecksumAlgorithm.MD5.value == "md5"
        assert ChecksumAlgorithm.SHA1.value == "sha1"
        assert ChecksumAlgorithm.SHA256.value == "sha256"
        assert ChecksumAlgorithm.SHA512.value == "sha512"


class TestBackupStatus:
    """Tests for BackupStatus enum."""

    def test_status_values(self):
        assert BackupStatus.PENDING.value == "pending"
        assert BackupStatus.VERIFYING.value == "verifying"
        assert BackupStatus.VERIFIED.value == "verified"
        assert BackupStatus.FAILED.value == "failed"
        assert BackupStatus.CORRUPTED.value == "corrupted"


class TestBackupManifest:
    """Tests for BackupManifest class."""

    def test_create_manifest(self):
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        assert manifest.backup_id == "backup-001"
        assert manifest.algorithm == ChecksumAlgorithm.SHA256
        assert len(manifest.files) == 0

    def test_add_file(self):
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        manifest.add_file("file1.txt", "abc123", 1024)
        assert len(manifest.files) == 1
        assert manifest.files[0]["path"] == "file1.txt"

    def test_get_checksum(self):
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        manifest.add_file("file1.txt", "abc123", 1024)
        assert manifest.get_checksum("file1.txt") == "abc123"
        assert manifest.get_checksum("missing.txt") is None

    def test_total_size(self):
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        manifest.add_file("file1.txt", "abc123", 1024)
        manifest.add_file("file2.txt", "def456", 2048)
        assert manifest.total_size() == 3072


class TestBackupIntegrity:
    """Tests for BackupIntegrity class."""

    def test_compute_checksum_sha256(self):
        integrity = BackupIntegrity()
        checksum = integrity.compute_checksum("hello world", ChecksumAlgorithm.SHA256)
        assert len(checksum) == 64  # SHA256 hex length

    def test_compute_checksum_md5(self):
        integrity = BackupIntegrity()
        checksum = integrity.compute_checksum("hello world", ChecksumAlgorithm.MD5)
        assert len(checksum) == 32  # MD5 hex length

    def test_verify_checksum(self):
        integrity = BackupIntegrity()
        data = "test data"
        expected = integrity.compute_checksum(data, ChecksumAlgorithm.SHA256)
        assert integrity.verify_checksum(data, expected, ChecksumAlgorithm.SHA256)

    def test_verify_checksum_fail(self):
        integrity = BackupIntegrity()
        data = "test data"
        assert not integrity.verify_checksum(data, "wrong_checksum", ChecksumAlgorithm.SHA256)

    def test_compute_checksum_consistent(self):
        integrity = BackupIntegrity()
        c1 = integrity.compute_checksum("same data", ChecksumAlgorithm.SHA256)
        c2 = integrity.compute_checksum("same data", ChecksumAlgorithm.SHA256)
        assert c1 == c2


class TestVerificationResult:
    """Tests for VerificationResult class."""

    def test_success_result(self):
        result = VerificationResult(
            backup_id="backup-001",
            status=BackupStatus.VERIFIED,
            files_checked=10,
            files_passed=10,
        )
        assert result.status == BackupStatus.VERIFIED
        assert result.is_success()

    def test_failure_result(self):
        result = VerificationResult(
            backup_id="backup-001",
            status=BackupStatus.FAILED,
            files_checked=10,
            files_passed=8,
            errors=["file3.txt: checksum mismatch"],
        )
        assert result.status == BackupStatus.FAILED
        assert not result.is_success()
        assert len(result.errors) == 1

    def test_corrupted_result(self):
        result = VerificationResult(
            backup_id="backup-001",
            status=BackupStatus.CORRUPTED,
            files_checked=5,
            files_passed=0,
        )
        assert result.status == BackupStatus.CORRUPTED
        assert not result.is_success()


class TestBackupVerifier:
    """Tests for BackupVerifier class."""

    def test_verify_manifest(self):
        verifier = BackupVerifier()
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        data = "file content"
        checksum = verifier._compute_checksum(data, ChecksumAlgorithm.SHA256)
        manifest.add_file("file1.txt", checksum, len(data))

        result = verifier.verify_manifest(manifest, {"file1.txt": data})
        assert result.status == BackupStatus.VERIFIED

    def test_verify_manifest_mismatch(self):
        verifier = BackupVerifier()
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        manifest.add_file("file1.txt", "wrong_checksum", 100)

        result = verifier.verify_manifest(manifest, {"file1.txt": "actual content"})
        assert result.status == BackupStatus.FAILED

    def test_verify_manifest_missing_file(self):
        verifier = BackupVerifier()
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        data = "file content"
        checksum = verifier._compute_checksum(data, ChecksumAlgorithm.SHA256)
        manifest.add_file("file1.txt", checksum, len(data))

        result = verifier.verify_manifest(manifest, {})
        assert result.status == BackupStatus.FAILED

    def test_verify_empty_manifest(self):
        verifier = BackupVerifier()
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        result = verifier.verify_manifest(manifest, {})
        assert result.status == BackupStatus.VERIFIED

    def test_generate_verification_report(self):
        verifier = BackupVerifier()
        manifest = BackupManifest(backup_id="backup-001", algorithm=ChecksumAlgorithm.SHA256)
        data = "file content"
        checksum = verifier._compute_checksum(data, ChecksumAlgorithm.SHA256)
        manifest.add_file("file1.txt", checksum, len(data))

        result = verifier.verify_manifest(manifest, {"file1.txt": data})
        report = verifier.generate_report(result)
        assert "backup-001" in report
        assert "verified" in report.lower()
