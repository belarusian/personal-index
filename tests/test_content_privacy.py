"""Tests for content_privacy module - Privacy controls and data handling."""

from __future__ import annotations

import pytest
from personal_index.content_privacy import (
    ConsentManager,
    ConsentRecord,
    DataClassification,
    DataMinimizer,
    PrivacyConfig,
    PrivacyPolicy,
    classify_data,
)


class TestDataClassification:
    """Tests for DataClassification enum and utilities."""

    def test_classification_levels(self):
        assert DataClassification.PUBLIC.value == "public"
        assert DataClassification.PRIVATE.value == "private"
        assert DataClassification.SENSITIVE.value == "sensitive"
        assert DataClassification.CONFIDENTIAL.value == "confidential"

    def test_classification_order(self):
        levels = [DataClassification.PUBLIC, DataClassification.PRIVATE,
                   DataClassification.SENSITIVE, DataClassification.CONFIDENTIAL]
        assert levels[0].level < levels[1].level < levels[2].level < levels[3].level

    def test_classify_email(self):
        assert classify_data("user@example.com") == DataClassification.SENSITIVE

    def test_classify_plain_text(self):
        assert classify_data("Hello world") == DataClassification.PUBLIC

    def test_classify_credit_card(self):
        assert classify_data("4111-1111-1111-1111") == DataClassification.CONFIDENTIAL


class TestPrivacyConfig:
    """Tests for PrivacyConfig class."""

    def test_default_config(self):
        config = PrivacyConfig()
        assert config.anonymize_ips is True
        assert config.track_analytics is False

    def test_custom_config(self):
        config = PrivacyConfig(anonymize_ips=False, track_analytics=True)
        assert config.anonymize_ips is False
        assert config.track_analytics is True

    def test_config_to_dict(self):
        config = PrivacyConfig()
        result = config.to_dict()
        assert isinstance(result, dict)
        assert "anonymize_ips" in result

    def test_config_from_dict(self):
        data = {"anonymize_ips": False, "track_analytics": True}
        config = PrivacyConfig.from_dict(data)
        assert config.anonymize_ips is False
        assert config.track_analytics is True


class TestPrivacyPolicy:
    """Tests for PrivacyPolicy class."""

    def test_policy_summary(self):
        policy = PrivacyPolicy(
            name="Test Policy",
            version="2.0",
            data_collected=["email", "name"],
        )
        summary = policy.get_summary()
        assert "Test Policy" in summary
        assert "v2.0" in summary

    def test_default_user_rights(self):
        policy = PrivacyPolicy(name="Test")
        assert "access" in policy.user_rights
        assert "erasure" in policy.user_rights


class TestDataMinimizer:
    """Tests for DataMinimizer class."""

    def test_mask_email(self):
        result = DataMinimizer.mask_email("user@example.com")
        assert "@" in result
        assert "user" not in result

    def test_mask_phone(self):
        result = DataMinimizer.mask_phone("+1234567890")
        assert "7890" in result
        assert "1234" not in result

    def test_redact_sensitive_fields(self):
        data = {"name": "John", "email": "john@test.com", "age": 30}
        result = DataMinimizer.redact_sensitive_fields(data, ["email"])
        assert "email" in result
        assert "john@test.com" not in result["email"]

    def test_hash_value(self):
        h1 = DataMinimizer.hash_value("secret")
        h2 = DataMinimizer.hash_value("secret")
        assert h1 == h2
        assert h1 != "secret"

    def test_truncate_content(self):
        long_text = "a" * 500
        result = DataMinimizer.truncate_content(long_text, 100)
        assert len(result) <= 100


class TestConsentManager:
    """Tests for ConsentManager class."""

    def test_record_consent(self):
        manager = ConsentManager()
        record = manager.record_consent("user1", "analytics", True)
        assert record.user_id == "user1"
        assert record.granted is True

    def test_has_consent(self):
        manager = ConsentManager()
        manager.record_consent("user1", "analytics", True)
        assert manager.has_consent("user1", "analytics")

    def test_no_consent(self):
        manager = ConsentManager()
        assert not manager.has_consent("user1", "analytics")

    def test_withdraw_consent(self):
        manager = ConsentManager()
        manager.record_consent("user1", "analytics", True)
        assert manager.withdraw_consent("user1", "analytics")
        assert not manager.has_consent("user1", "analytics")

    def test_get_records_filtered(self):
        manager = ConsentManager()
        manager.record_consent("user1", "analytics", True)
        manager.record_consent("user2", "cookies", True)
        records = manager.get_records("user1")
        assert len(records) == 1
        assert records[0].user_id == "user1"


class TestIPAnonymizer:
    """Tests for IPAnonymizer class."""

    def test_anonymize_ipv4_default(self):
        from personal_index.content_privacy import IPAnonymizer
        result = IPAnonymizer.anonymize_ipv4("192.168.1.100")
        assert result == "192.168.1.0"

    def test_anonymize_ipv4_custom_mask(self):
        from personal_index.content_privacy import IPAnonymizer
        result = IPAnonymizer.anonymize_ipv4("192.168.1.100", mask_bits=16)
        assert result == "192.168.0.0"

    def test_anonymize_auto_detect(self):
        from personal_index.content_privacy import IPAnonymizer
        result = IPAnonymizer.anonymize("10.0.0.1")
        assert result == "10.0.0.0"

    def test_anonymize_invalid_ip(self):
        from personal_index.content_privacy import IPAnonymizer
        result = IPAnonymizer.anonymize_ipv4("not-an-ip")
        assert result == "not-an-ip"
