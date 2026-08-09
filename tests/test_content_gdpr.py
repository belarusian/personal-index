"""Tests for content_gdpr module - GDPR compliance tools."""

from __future__ import annotations

import pytest
from personal_index.content_gdpr import (
    DataPortability,
    DataProcessor,
    DataSubjectRequest,
    DSARStatus,
    GDPRComplianceChecker,
    LawfulBasis,
    RightToErasure,
)


class TestLawfulBasis:
    """Tests for LawfulBasis enum."""

    def test_basis_values(self):
        assert LawfulBasis.CONSENT.value == "consent"
        assert LawfulBasis.CONTRACT.value == "contract"
        assert LawfulBasis.LEGAL_OBLIGATION.value == "legal_obligation"
        assert LawfulBasis.VITAL_INTERESTS.value == "vital_interests"
        assert LawfulBasis.PUBLIC_TASK.value == "public_task"
        assert LawfulBasis.LEGITIMATE_INTERESTS.value == "legitimate_interests"


class TestDataSubjectRequest:
    """Tests for DataSubjectRequest class."""

    def test_create_request(self):
        request = DataSubjectRequest(
            user_id="user123",
            request_type="access",
            lawful_basis=LawfulBasis.CONSENT,
        )
        assert request.user_id == "user123"
        assert request.request_type == "access"
        assert request.status == DSARStatus.PENDING

    def test_request_completed(self):
        request = DataSubjectRequest(
            user_id="user123",
            request_type="erasure",
            lawful_basis=LawfulBasis.CONSENT,
        )
        request.mark_completed()
        assert request.status == DSARStatus.COMPLETED

    def test_request_rejected(self):
        request = DataSubjectRequest(
            user_id="user123",
            request_type="access",
            lawful_basis=LawfulBasis.CONSENT,
        )
        request.reject("Insufficient verification")
        assert request.status == DSARStatus.REJECTED
        assert request.rejection_reason == "Insufficient verification"

    def test_request_mark_processing(self):
        request = DataSubjectRequest(
            user_id="user123",
            request_type="access",
            lawful_basis=LawfulBasis.CONSENT,
        )
        request.mark_processing()
        assert request.status == DSARStatus.PROCESSING


class TestDSARStatus:
    """Tests for DSARStatus enum."""

    def test_status_values(self):
        assert DSARStatus.PENDING.value == "pending"
        assert DSARStatus.PROCESSING.value == "processing"
        assert DSARStatus.COMPLETED.value == "completed"
        assert DSARStatus.REJECTED.value == "rejected"


class TestGDPRComplianceChecker:
    """Tests for GDPRComplianceChecker class."""

    def test_check_retention_policy(self):
        checker = GDPRComplianceChecker()
        result = checker.check_retention_policy(90)
        assert result.compliant is True

    def test_check_retention_exceeded(self):
        checker = GDPRComplianceChecker()
        result = checker.check_retention_policy(400)
        assert result.compliant is False

    def test_check_data_minimization(self):
        checker = GDPRComplianceChecker()
        result = checker.check_data_minimization(["name", "email"], ["name", "email"])
        assert result.compliant is True

    def test_check_data_minimization_excess(self):
        checker = GDPRComplianceChecker()
        result = checker.check_data_minimization(["name"], ["name", "email", "ssn"])
        assert result.compliant is False

    def test_check_purpose_limitation(self):
        checker = GDPRComplianceChecker()
        result = checker.check_purpose_limitation("analytics", ["analytics", "marketing"])
        assert result.compliant is True

    def test_check_purpose_limitation_violation(self):
        checker = GDPRComplianceChecker()
        result = checker.check_purpose_limitation("sales", ["analytics"])
        assert result.compliant is False

    def test_run_full_check(self):
        checker = GDPRComplianceChecker()
        results = checker.run_full_check(
            retention_days=90,
            required_fields=["name"],
            collected_fields=["name"],
            processing_purpose="analytics",
            declared_purposes=["analytics"],
        )
        assert len(results) == 3
        assert all(r.compliant for r in results)


class TestDataProcessor:
    """Tests for DataProcessor class."""

    def test_anonymize_record(self):
        processor = DataProcessor()
        data = {"name": "John Doe", "email": "john@example.com", "age": 30}
        result = processor.anonymize_record(data, ["name", "email"])
        assert "John Doe" not in result["name"]
        assert "john@example.com" not in result["email"]
        assert result["age"] == 30

    def test_pseudonymize(self):
        processor = DataProcessor()
        result = processor.pseudonymize("John Doe")
        assert result != "John Doe"
        assert isinstance(result, str)

    def test_export_user_data(self):
        processor = DataProcessor()
        data = {"name": "John", "email": "john@test.com"}
        result = processor.export_user_data(data)
        assert "data" in result
        assert result["data"]["name"] == "John"
        assert "exported_at" in result


class TestRightToErasure:
    """Tests for RightToErasure class."""

    def test_erasure_request(self):
        erasure = RightToErasure()
        result = erasure.request_erasure("user123", ["profile", "logs"])
        assert result.user_id == "user123"
        assert "profile" in result.data_categories

    def test_erasure_with_reason(self):
        erasure = RightToErasure()
        result = erasure.request_erasure("user123", ["profile"], reason="withdrawn consent")
        assert result.reason == "withdrawn consent"

    def test_get_pending_requests(self):
        erasure = RightToErasure()
        erasure.request_erasure("user123", ["profile"])
        pending = erasure.get_pending_requests()
        assert len(pending) == 1

    def test_complete_erasure(self):
        erasure = RightToErasure()
        req = erasure.request_erasure("user123", ["profile"])
        assert erasure.complete_erasure(req.request_id)
        assert req.status == DSARStatus.COMPLETED


class TestDataPortability:
    """Tests for DataPortability class."""

    def test_export_json(self):
        portability = DataPortability()
        data = {"name": "John", "email": "john@test.com"}
        result = portability.export_as_json(data)
        assert isinstance(result, str)
        assert "John" in result

    def test_export_format(self):
        portability = DataPortability()
        data = {"name": "John"}
        result = portability.export_as_json(data)
        assert result.startswith("{")
        assert result.endswith("}")

    def test_export_csv(self):
        portability = DataPortability()
        data = [{"name": "John", "age": "30"}, {"name": "Jane", "age": "25"}]
        result = portability.export_as_csv(data)
        assert "name,age" in result
        assert "John,30" in result

    def test_export_csv_empty(self):
        portability = DataPortability()
        result = portability.export_as_csv([])
        assert result == ""


class TestDataRetentionPolicy:
    """Tests for DataRetentionPolicy class."""

    def test_expired_data(self):
        from personal_index.content_gdpr import DataRetentionPolicy
        policy = DataRetentionPolicy(name="logs", max_retention_days=90)
        assert policy.is_expired(91)
        assert not policy.is_expired(89)

    def test_notification_due(self):
        from personal_index.content_gdpr import DataRetentionPolicy
        policy = DataRetentionPolicy(name="logs", max_retention_days=90, notification_days_before=14)
        assert policy.should_notify(80)  # 10 days remaining
        assert not policy.should_notify(70)  # 20 days remaining

    def test_category_match(self):
        from personal_index.content_gdpr import DataRetentionPolicy
        policy = DataRetentionPolicy(name="logs", max_retention_days=90, data_categories=["logs", "analytics"])
        assert policy.matches_category("logs")
        assert not policy.matches_category("user_data")

    def test_no_category_filter(self):
        from personal_index.content_gdpr import DataRetentionPolicy
        policy = DataRetentionPolicy(name="all", max_retention_days=90)
        assert policy.matches_category("anything")
