"""Tests for content_audit module - Audit logging and tracking."""

from __future__ import annotations

import pytest
from personal_index.content_audit import (
    AuditEntry,
    AuditEventType,
    AuditLog,
    AuditLogLevel,
    AuditQuery,
    AuditReporter,
)


class TestAuditEventType:
    """Tests for AuditEventType enum."""

    def test_event_types(self):
        assert AuditEventType.CREATE.value == "create"
        assert AuditEventType.READ.value == "read"
        assert AuditEventType.UPDATE.value == "update"
        assert AuditEventType.DELETE.value == "delete"
        assert AuditEventType.ACCESS.value == "access"
        assert AuditEventType.EXPORT.value == "export"


class TestAuditLogLevel:
    """Tests for AuditLogLevel enum."""

    def test_log_levels(self):
        assert AuditLogLevel.INFO.value == "info"
        assert AuditLogLevel.WARNING.value == "warning"
        assert AuditLogLevel.ERROR.value == "error"
        assert AuditLogLevel.CRITICAL.value == "critical"

    def test_log_level_order(self):
        levels = [AuditLogLevel.INFO, AuditLogLevel.WARNING,
                   AuditLogLevel.ERROR, AuditLogLevel.CRITICAL]
        assert levels[0].level < levels[1].level < levels[2].level < levels[3].level


class TestAuditEntry:
    """Tests for AuditEntry class."""

    def test_create_entry(self):
        entry = AuditEntry(
            event_type=AuditEventType.CREATE,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
        )
        assert entry.event_type == AuditEventType.CREATE
        assert entry.resource_type == "document"
        assert entry.resource_id == "doc-001"

    def test_entry_with_details(self):
        entry = AuditEntry(
            event_type=AuditEventType.UPDATE,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
            details={"field": "title", "old_value": "Old", "new_value": "New"},
        )
        assert entry.details == {"field": "title", "old_value": "Old", "new_value": "New"}

    def test_entry_default_level(self):
        entry = AuditEntry(
            event_type=AuditEventType.READ,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
        )
        assert entry.log_level == AuditLogLevel.INFO


class TestAuditLog:
    """Tests for AuditLog class."""

    def test_add_entry(self):
        log = AuditLog()
        entry = AuditEntry(
            event_type=AuditEventType.CREATE,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
        )
        log.add_entry(entry)
        assert len(log.entries) == 1

    def test_filter_by_event_type(self):
        log = AuditLog()
        log.add_entry(AuditEntry(
            event_type=AuditEventType.CREATE,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
        ))
        log.add_entry(AuditEntry(
            event_type=AuditEventType.DELETE,
            resource_type="document",
            resource_id="doc-002",
            user_id="user-123",
        ))
        results = log.filter(event_type=AuditEventType.CREATE)
        assert len(results) == 1

    def test_filter_by_user(self):
        log = AuditLog()
        log.add_entry(AuditEntry(
            event_type=AuditEventType.CREATE,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
        ))
        log.add_entry(AuditEntry(
            event_type=AuditEventType.CREATE,
            resource_type="document",
            resource_id="doc-002",
            user_id="user-456",
        ))
        results = log.filter(user_id="user-123")
        assert len(results) == 1

    def test_filter_by_resource(self):
        log = AuditLog()
        log.add_entry(AuditEntry(
            event_type=AuditEventType.CREATE,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
        ))
        results = log.filter(resource_id="doc-001")
        assert len(results) == 1

    def test_filter_by_log_level(self):
        log = AuditLog()
        log.add_entry(AuditEntry(
            event_type=AuditEventType.CREATE,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
            log_level=AuditLogLevel.INFO,
        ))
        log.add_entry(AuditEntry(
            event_type=AuditEventType.DELETE,
            resource_type="document",
            resource_id="doc-002",
            user_id="user-123",
            log_level=AuditLogLevel.WARNING,
        ))
        results = log.filter(min_level=AuditLogLevel.WARNING)
        assert len(results) == 1

    def test_get_recent(self):
        log = AuditLog()
        for i in range(10):
            log.add_entry(AuditEntry(
                event_type=AuditEventType.CREATE,
                resource_type="document",
                resource_id=f"doc-{i}",
                user_id="user-123",
            ))
        recent = log.get_recent(5)
        assert len(recent) == 5

    def test_clear_old_entries(self):
        log = AuditLog()
        for i in range(100):
            log.add_entry(AuditEntry(
                event_type=AuditEventType.CREATE,
                resource_type="document",
                resource_id=f"doc-{i}",
                user_id="user-123",
            ))
        log.clear_old_entries(max_entries=50)
        assert len(log.entries) == 50


class TestAuditQuery:
    """Tests for AuditQuery class."""

    def test_basic_query(self):
        query = AuditQuery(event_type=AuditEventType.CREATE)
        assert query.event_type == AuditEventType.CREATE

    def test_query_with_multiple_filters(self):
        query = AuditQuery(
            event_type=AuditEventType.CREATE,
            user_id="user-123",
            resource_type="document",
            min_level=AuditLogLevel.WARNING,
        )
        assert query.event_type == AuditEventType.CREATE
        assert query.user_id == "user-123"
        assert query.resource_type == "document"
        assert query.min_level == AuditLogLevel.WARNING


class TestAuditReporter:
    """Tests for AuditReporter class."""

    def test_generate_summary(self):
        log = AuditLog()
        for i in range(5):
            log.add_entry(AuditEntry(
                event_type=AuditEventType.CREATE,
                resource_type="document",
                resource_id=f"doc-{i}",
                user_id="user-123",
            ))
        reporter = AuditReporter()
        summary = reporter.generate_summary(log)
        assert summary["total_entries"] == 5
        assert summary["event_counts"] is not None

    def test_generate_report_by_user(self):
        log = AuditLog()
        log.add_entry(AuditEntry(
            event_type=AuditEventType.CREATE,
            resource_type="document",
            resource_id="doc-001",
            user_id="user-123",
        ))
        reporter = AuditReporter()
        report = reporter.generate_report_by_user(log, "user-123")
        assert len(report) == 1

    def test_detect_anomalies(self):
        log = AuditLog()
        for i in range(20):
            log.add_entry(AuditEntry(
                event_type=AuditEventType.DELETE,
                resource_type="document",
                resource_id=f"doc-{i}",
                user_id="user-123",
            ))
        reporter = AuditReporter()
        anomalies = reporter.detect_anomalies(log)
        assert len(anomalies) > 0
