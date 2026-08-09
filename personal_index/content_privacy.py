"""Content privacy module - Privacy controls, data classification, and minimization."""

from __future__ import annotations

import datetime
import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class DataClassification(str, Enum):
    """Data classification levels for privacy handling."""

    PUBLIC = "public"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    CONFIDENTIAL = "confidential"

    @property
    def level(self) -> int:
        """Return numeric sensitivity level (higher = more sensitive)."""
        levels = {
            "public": 0,
            "private": 1,
            "sensitive": 2,
            "confidential": 3,
        }
        return levels[self.value]


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\+?\d{10,}")
CC_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")


def classify_data(text: str) -> DataClassification:
    """Classify data sensitivity based on content patterns.

    Args:
        text: Text content to classify.

    Returns:
        DataClassification level for the content.
    """
    if CC_PATTERN.search(text):
        return DataClassification.CONFIDENTIAL
    if EMAIL_PATTERN.search(text):
        return DataClassification.SENSITIVE
    if PHONE_PATTERN.search(text):
        return DataClassification.SENSITIVE
    return DataClassification.PUBLIC


@dataclass
class PrivacyConfig:
    """Privacy configuration settings."""

    anonymize_ips: bool = True
    track_analytics: bool = False
    data_retention_days: int = 90
    allow_cookies: bool = False
    share_with_third_party: bool = False
    enable_encryption: bool = True
    min_classification: DataClassification = DataClassification.PUBLIC

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Dictionary representation of the config.
        """
        return {
            "anonymize_ips": self.anonymize_ips,
            "track_analytics": self.track_analytics,
            "data_retention_days": self.data_retention_days,
            "allow_cookies": self.allow_cookies,
            "share_with_third_party": self.share_with_third_party,
            "enable_encryption": self.enable_encryption,
            "min_classification": self.min_classification.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PrivacyConfig:
        """Create config from dictionary.

        Args:
            data: Dictionary with config values.

        Returns:
            PrivacyConfig instance.
        """
        return cls(
            anonymize_ips=data.get("anonymize_ips", True),
            track_analytics=data.get("track_analytics", False),
            data_retention_days=data.get("data_retention_days", 90),
            allow_cookies=data.get("allow_cookies", False),
            share_with_third_party=data.get("share_with_third_party", False),
            enable_encryption=data.get("enable_encryption", True),
        )


@dataclass
class PrivacyPolicy:
    """Privacy policy document for a data collection."""

    name: str
    version: str = "1.0"
    description: str = ""
    data_collected: list[str] = field(default_factory=list)
    data_retention_days: int = 90
    third_party_sharing: bool = False
    user_rights: list[str] = field(default_factory=lambda: [
        "access", "rectification", "erasure", "portability",
    ])

    def get_summary(self) -> str:
        """Get a human-readable summary of the policy.

        Returns:
            Summary string describing the policy.
        """
        parts = [f"Policy: {self.name} v{self.version}"]
        if self.description:
            parts.append(f"Description: {self.description}")
        parts.append(f"Data collected: {', '.join(self.data_collected) if self.data_collected else 'None'}")
        parts.append(f"Retention: {self.data_retention_days} days")
        parts.append(f"Third-party sharing: {'Yes' if self.third_party_sharing else 'No'}")
        return "\n".join(parts)


class DataMinimizer:
    """Utility for data minimization and anonymization."""

    @staticmethod
    def mask_email(email: str, visible_chars: int = 2) -> str:
        """Mask an email address, showing only first few chars.

        Args:
            email: Email address to mask.
            visible_chars: Number of visible characters before masking.

        Returns:
            Masked email string.
        """
        if "@" not in email:
            return "***"
        local, domain = email.split("@", 1)
        masked_local = local[:visible_chars] + "***"
        return f"{masked_local}@{domain}"

    @staticmethod
    def mask_phone(phone: str, visible_digits: int = 4) -> str:
        """Mask a phone number, showing only last digits.

        Args:
            phone: Phone number to mask.
            visible_digits: Number of visible digits at the end.

        Returns:
            Masked phone string.
        """
        digits = re.sub(r"\D", "", phone)
        if len(digits) <= visible_digits:
            return "***"
        masked = "*" * (len(digits) - visible_digits) + digits[-visible_digits:]
        return masked

    @staticmethod
    def redact_sensitive_fields(data: dict, sensitive_fields: list[str]) -> dict:
        """Redact sensitive fields from a data dictionary.

        Args:
            data: Dictionary containing data fields.
            sensitive_fields: List of field names to redact.

        Returns:
            Dictionary with sensitive fields redacted.
        """
        result = dict(data)
        for field_name in sensitive_fields:
            if field_name in result:
                value = result[field_name]
                if isinstance(value, str) and "@" in value:
                    result[field_name] = DataMinimizer.mask_email(value)
                elif isinstance(value, str) and re.match(r"\+?\d{10,}", value):
                    result[field_name] = DataMinimizer.mask_phone(value)
                else:
                    result[field_name] = "***REDACTED***"
        return result

    @staticmethod
    def hash_value(value: str, salt: str = "personal_index") -> str:
        """Create a one-way hash of a value.

        Args:
            value: Value to hash.
            salt: Salt to prepend for security.

        Returns:
            SHA-256 hex digest of the salted value.
        """
        return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()

    @staticmethod
    def truncate_content(content: str, max_length: int) -> str:
        """Truncate content to maximum length.

        Args:
            content: Content string to truncate.
            max_length: Maximum allowed length.

        Returns:
            Truncated string with ellipsis if shortened.
        """
        if len(content) <= max_length:
            return content
        return content[:max_length - 3] + "..."


@dataclass
class ConsentRecord:
    """A record of user consent."""

    user_id: str
    consent_type: str
    granted: bool
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    withdrawn_at: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ConsentManager:
    """Manages user consent records for privacy compliance."""

    def __init__(self) -> None:
        self._records: list[ConsentRecord] = []

    def record_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentRecord:
        """Record a user's consent decision.

        Args:
            user_id: Unique user identifier.
            consent_type: Type of consent (e.g., 'analytics', 'cookies').
            granted: Whether consent was granted.
            ip_address: User's IP address (optional).
            user_agent: User's browser agent (optional).

        Returns:
            The created ConsentRecord.
        """
        record = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._records.append(record)
        return record

    def withdraw_consent(self, user_id: str, consent_type: str) -> bool:
        """Withdraw a user's consent.

        Args:
            user_id: Unique user identifier.
            consent_type: Type of consent to withdraw.

        Returns:
            True if consent was found and withdrawn.
        """
        for record in self._records:
            if record.user_id == user_id and record.consent_type == consent_type:
                record.withdrawn_at = datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat()
                return True
        return False

    def has_consent(self, user_id: str, consent_type: str) -> bool:
        """Check if a user has active consent for a type.

        Args:
            user_id: Unique user identifier.
            consent_type: Type of consent to check.

        Returns:
            True if user has active (non-withdrawn) consent.
        """
        for record in reversed(self._records):
            if record.user_id == user_id and record.consent_type == consent_type:
                return record.granted and record.withdrawn_at is None
        return False

    def get_records(self, user_id: Optional[str] = None) -> list[ConsentRecord]:
        """Get consent records, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter by.

        Returns:
            List of matching consent records.
        """
        if user_id:
            return [r for r in self._records if r.user_id == user_id]
        return list(self._records)


class IPAnonymizer:
    """Anonymizes IP addresses for privacy compliance."""

    @staticmethod
    def anonymize_ipv4(ip: str, mask_bits: int = 24) -> str:
        """Anonymize an IPv4 address by zeroing out last bits.

        Args:
            ip: IPv4 address string.
            mask_bits: Number of bits to preserve (default 24 = /24).

        Returns:
            Anonymized IP address string.
        """
        parts = ip.split(".")
        if len(parts) != 4:
            return ip
        octets = [int(p) for p in parts]
        bytes_to_zero = 4 - (mask_bits // 8)
        for i in range(bytes_to_zero):
            octets[-(i + 1)] = 0
        return ".".join(str(o) for o in octets)

    @staticmethod
    def anonymize_ipv6(ip: str, mask_bits: int = 56) -> str:
        """Anonymize an IPv6 address by zeroing out last bits.

        Args:
            ip: IPv6 address string.
            mask_bits: Number of bits to preserve (default 56 = /56).

        Returns:
            Anonymized IPv6 address string.
        """
        # Simple approach: zero out last groups
        groups = ip.split(":")
        groups_to_zero = 8 - (mask_bits // 16)
        for i in range(groups_to_zero):
            groups[-(i + 1)] = "0"
        return ":".join(groups)

    @staticmethod
    def anonymize(ip: str) -> str:
        """Anonymize an IP address (auto-detects IPv4/IPv6).

        Args:
            ip: IP address string.

        Returns:
            Anonymized IP address string.
        """
        if "." in ip and ":" not in ip:
            return IPAnonymizer.anonymize_ipv4(ip)
        return IPAnonymizer.anonymize_ipv6(ip)
