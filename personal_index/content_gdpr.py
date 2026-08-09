"""Content GDPR module - GDPR compliance tools and data subject rights."""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class LawfulBasis(str, Enum):
    """GDPR lawful basis for processing personal data."""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DSARStatus(str, Enum):
    """Status of a Data Subject Access Request."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


@dataclass
class ComplianceResult:
    """Result of a compliance check."""

    compliant: bool
    check_name: str
    details: str = ""
    recommendations: list[str] = field(default_factory=list)


@dataclass
class DataSubjectRequest:
    """A data subject access request (DSAR)."""

    user_id: str
    request_type: str
    lawful_basis: LawfulBasis
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: DSARStatus = DSARStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    notes: str = ""

    def mark_completed(self) -> None:
        """Mark the request as completed."""
        self.status = DSARStatus.COMPLETED
        self.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def mark_processing(self) -> None:
        """Mark the request as being processed."""
        self.status = DSARStatus.PROCESSING

    def reject(self, reason: str) -> None:
        """Reject the request with a reason.

        Args:
            reason: Explanation for the rejection.
        """
        self.status = DSARStatus.REJECTED
        self.rejection_reason = reason


@dataclass
class ErasureRequest:
    """A right-to-erasure (right to be forgotten) request."""

    user_id: str
    data_categories: list[str]
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    reason: str = ""
    status: DSARStatus = DSARStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None


class GDPRComplianceChecker:
    """Checks data processing activities against GDPR requirements."""

    MAX_RETENTION_DAYS = 365  # Default max retention

    def check_retention_policy(self, retention_days: int) -> ComplianceResult:
        """Check if data retention period is compliant.

        Args:
            retention_days: Number of days data is retained.

        Returns:
            ComplianceResult with check outcome.
        """
        if retention_days <= self.MAX_RETENTION_DAYS:
            return ComplianceResult(
                compliant=True,
                check_name="retention_policy",
                details=f"Retention period of {retention_days} days is within limit",
            )
        return ComplianceResult(
            compliant=False,
            check_name="retention_policy",
            details=f"Retention period of {retention_days} days exceeds {self.MAX_RETENTION_DAYS} day limit",
            recommendations=[
                f"Reduce retention period to {self.MAX_RETENTION_DAYS} days or less",
                "Implement automatic data deletion",
            ],
        )

    def check_data_minimization(
        self, required_fields: list[str], collected_fields: list[str]
    ) -> ComplianceResult:
        """Check if data collection follows minimization principle.

        Args:
            required_fields: Fields actually needed for the purpose.
            collected_fields: Fields currently being collected.

        Returns:
            ComplianceResult with check outcome.
        """
        excess = set(collected_fields) - set(required_fields)
        if not excess:
            return ComplianceResult(
                compliant=True,
                check_name="data_minimization",
                details="Only necessary data is collected",
            )
        return ComplianceResult(
            compliant=False,
            check_name="data_minimization",
            details=f"Excess fields collected: {', '.join(excess)}",
            recommendations=[
                f"Stop collecting unnecessary fields: {', '.join(excess)}",
            ],
        )

    def check_purpose_limitation(
        self, processing_purpose: str, declared_purposes: list[str]
    ) -> ComplianceResult:
        """Check if data processing is limited to declared purposes.

        Args:
            processing_purpose: The actual purpose of processing.
            declared_purposes: Purposes declared to the data subject.

        Returns:
            ComplianceResult with check outcome.
        """
        if processing_purpose in declared_purposes:
            return ComplianceResult(
                compliant=True,
                check_name="purpose_limitation",
                details=f"Purpose '{processing_purpose}' is within declared purposes",
            )
        return ComplianceResult(
            compliant=False,
            check_name="purpose_limitation",
            details=f"Purpose '{processing_purpose}' not in declared purposes: {', '.join(declared_purposes)}",
            recommendations=[
                f"Add '{processing_purpose}' to declared purposes with user consent",
                "Stop processing for undeclared purpose",
            ],
        )

    def run_full_check(
        self,
        retention_days: int,
        required_fields: list[str],
        collected_fields: list[str],
        processing_purpose: str,
        declared_purposes: list[str],
    ) -> list[ComplianceResult]:
        """Run all GDPR compliance checks.

        Returns:
            List of ComplianceResult for each check.
        """
        return [
            self.check_retention_policy(retention_days),
            self.check_data_minimization(required_fields, collected_fields),
            self.check_purpose_limitation(processing_purpose, declared_purposes),
        ]


class DataProcessor:
    """Utilities for GDPR-compliant data processing."""

    @staticmethod
    def anonymize_record(record: dict, fields_to_anonymize: list[str]) -> dict:
        """Anonymize specified fields in a data record.

        Args:
            record: Data record dictionary.
            fields_to_anonymize: List of field names to anonymize.

        Returns:
            Dictionary with specified fields anonymized.
        """
        result = dict(record)
        for field_name in fields_to_anonymize:
            if field_name in result:
                value = str(result[field_name])
                result[field_name] = f"[ANONYMIZED:{hashlib.sha256(value.encode()).hexdigest()[:8]}]"
        return result

    @staticmethod
    def pseudonymize(value: str, salt: str = "gdpr_salt") -> str:
        """Create a pseudonym (reversible hash) for a value.

        Args:
            value: Value to pseudonymize.
            salt: Salt for the hash.

        Returns:
            Pseudonymized string.
        """
        return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]

    @staticmethod
    def export_user_data(data: dict) -> dict:
        """Prepare user data for export (right to portability).

        Args:
            data: User data dictionary.

        Returns:
            Export-ready dictionary with metadata.
        """
        return {
            "data": data,
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "format": "json",
            "version": "1.0",
        }


class RightToErasure:
    """Handles right-to-erasure (right to be forgotten) requests."""

    def __init__(self) -> None:
        self._requests: list[ErasureRequest] = []

    def request_erasure(
        self,
        user_id: str,
        data_categories: list[str],
        reason: str = "",
    ) -> ErasureRequest:
        """Create an erasure request.

        Args:
            user_id: User requesting erasure.
            data_categories: Categories of data to erase.
            reason: Optional reason for erasure.

        Returns:
            The created ErasureRequest.
        """
        request = ErasureRequest(
            user_id=user_id,
            data_categories=data_categories,
            reason=reason,
        )
        self._requests.append(request)
        return request

    def get_pending_requests(self) -> list[ErasureRequest]:
        """Get all pending erasure requests.

        Returns:
            List of pending ErasureRequest objects.
        """
        return [r for r in self._requests if r.status == DSARStatus.PENDING]

    def complete_erasure(self, request_id: str) -> bool:
        """Mark an erasure request as completed.

        Args:
            request_id: ID of the request to complete.

        Returns:
            True if request was found and completed.
        """
        for request in self._requests:
            if request.request_id == request_id:
                request.status = DSARStatus.COMPLETED
                request.completed_at = datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat()
                return True
        return False


class DataPortability:
    """Handles data portability requests (GDPR Article 20)."""

    @staticmethod
    def export_as_json(data: dict[str, Any]) -> str:
        """Export data as JSON string.

        Args:
            data: Data dictionary to export.

        Returns:
            JSON string representation.
        """
        export_data = {
            "data": data,
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "format": "json",
            "gdpr_article": "20",
        }
        return json.dumps(export_data, indent=2, default=str)

    @staticmethod
    def export_as_csv(data: list[dict[str, Any]]) -> str:
        """Export data as CSV string.

        Args:
            data: List of data dictionaries to export.

        Returns:
            CSV string representation.
        """
        if not data:
            return ""
        headers = list(data[0].keys())
        lines = [",".join(headers)]
        for row in data:
            values = [str(row.get(h, "")) for h in headers]
            lines.append(",".join(values))
        return "\n".join(lines)
