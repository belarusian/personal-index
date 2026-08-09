"""Tests for content_notifications module - in-app notification system."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from personal_index.content_notifications import (
    Notification,
    NotificationType,
    NotificationLevel,
    NotificationFilter,
    NotificationStore,
    NotificationPreferences,
)


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_notification_types(self):
        assert NotificationType.ITEM_SAVED.value == "item_saved"
        assert NotificationType.CRAWL_COMPLETE.value == "crawl_complete"
        assert NotificationType.CRAWL_ERROR.value == "crawl_error"
        assert NotificationType.INDEX_UPDATE.value == "index_update"
        assert NotificationType.SYSTEM.value == "system"
        assert NotificationType.ALERT.value == "alert"


class TestNotificationLevel:
    """Tests for NotificationLevel enum."""

    def test_level_values(self):
        assert NotificationLevel.INFO.value == "info"
        assert NotificationLevel.WARNING.value == "warning"
        assert NotificationLevel.ERROR.value == "error"
        assert NotificationLevel.SUCCESS.value == "success"

    def test_level_severity(self):
        assert NotificationLevel.ERROR.severity > NotificationLevel.INFO.severity
        assert NotificationLevel.WARNING.severity > NotificationLevel.INFO.severity


class TestNotification:
    """Tests for Notification model."""

    def test_create_notification(self):
        notif = Notification(
            title="New Item Saved",
            message="https://example.com was saved",
            notification_type=NotificationType.ITEM_SAVED,
        )
        assert notif.title == "New Item Saved"
        assert notif.message == "https://example.com was saved"
        assert notif.read is False
        assert notif.level == NotificationLevel.INFO

    def test_notification_with_level(self):
        notif = Notification(
            title="Error",
            message="Crawl failed",
            notification_type=NotificationType.CRAWL_ERROR,
            level=NotificationLevel.ERROR,
        )
        assert notif.level == NotificationLevel.ERROR

    def test_notification_with_data(self):
        notif = Notification(
            title="Crawl Complete",
            message="10 pages crawled",
            notification_type=NotificationType.CRAWL_COMPLETE,
            data={"pages": 10, "duration": 5.2},
        )
        assert notif.data["pages"] == 10

    def test_mark_read(self):
        notif = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM,
        )
        notif.mark_read()
        assert notif.read is True
        assert notif.read_at is not None

    def test_mark_unread(self):
        notif = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM,
        )
        notif.mark_read()
        notif.mark_unread()
        assert notif.read is False
        assert notif.read_at is None

    def test_notification_to_dict(self):
        notif = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM,
        )
        d = notif.to_dict()
        assert d["title"] == "Test"
        assert d["message"] == "Test message"
        assert d["read"] is False

    def test_notification_is_expired(self):
        past = datetime.now(timezone.utc) - timedelta(days=31)
        notif = Notification(
            title="Old",
            message="Old notification",
            notification_type=NotificationType.SYSTEM,
            created_at=past,
            ttl_days=30,
        )
        assert notif.is_expired() is True

    def test_notification_not_expired(self):
        notif = Notification(
            title="New",
            message="New notification",
            notification_type=NotificationType.SYSTEM,
            ttl_days=30,
        )
        assert notif.is_expired() is False

    def test_notification_no_expiry(self):
        notif = Notification(
            title="Permanent",
            message="Permanent notification",
            notification_type=NotificationType.SYSTEM,
        )
        assert notif.is_expired() is False


class TestNotificationFilter:
    """Tests for NotificationFilter."""

    def test_filter_by_type(self):
        filter_ = NotificationFilter(types=[NotificationType.ITEM_SAVED])
        notif_saved = Notification(
            title="Saved",
            message="Item saved",
            notification_type=NotificationType.ITEM_SAVED,
        )
        notif_error = Notification(
            title="Error",
            message="Error",
            notification_type=NotificationType.CRAWL_ERROR,
        )
        assert filter_.matches(notif_saved) is True
        assert filter_.matches(notif_error) is False

    def test_filter_by_level(self):
        filter_ = NotificationFilter(levels=[NotificationLevel.ERROR])
        notif_error = Notification(
            title="Error",
            message="Error",
            notification_type=NotificationType.CRAWL_ERROR,
            level=NotificationLevel.ERROR,
        )
        notif_info = Notification(
            title="Info",
            message="Info",
            notification_type=NotificationType.SYSTEM,
            level=NotificationLevel.INFO,
        )
        assert filter_.matches(notif_error) is True
        assert filter_.matches(notif_info) is False

    def test_filter_unread_only(self):
        filter_ = NotificationFilter(unread_only=True)
        notif_unread = Notification(
            title="Unread",
            message="Unread",
            notification_type=NotificationType.SYSTEM,
        )
        notif_read = Notification(
            title="Read",
            message="Read",
            notification_type=NotificationType.SYSTEM,
        )
        notif_read.mark_read()
        assert filter_.matches(notif_unread) is True
        assert filter_.matches(notif_read) is False

    def test_filter_combined(self):
        filter_ = NotificationFilter(
            types=[NotificationType.ITEM_SAVED],
            unread_only=True,
        )
        notif = Notification(
            title="Saved",
            message="Item saved",
            notification_type=NotificationType.ITEM_SAVED,
        )
        assert filter_.matches(notif) is True

    def test_filter_no_criteria(self):
        filter_ = NotificationFilter()
        notif = Notification(
            title="Any",
            message="Any notification",
            notification_type=NotificationType.SYSTEM,
        )
        assert filter_.matches(notif) is True


class TestNotificationPreferences:
    """Tests for NotificationPreferences."""

    def test_default_preferences(self):
        prefs = NotificationPreferences()
        assert prefs.enabled is True
        assert NotificationType.ITEM_SAVED in prefs.enabled_types

    def test_disable_type(self):
        prefs = NotificationPreferences()
        prefs.disable_type(NotificationType.CRAWL_COMPLETE)
        assert NotificationType.CRAWL_COMPLETE not in prefs.enabled_types

    def test_enable_type(self):
        prefs = NotificationPreferences()
        prefs.disable_type(NotificationType.CRAWL_COMPLETE)
        prefs.enable_type(NotificationType.CRAWL_COMPLETE)
        assert NotificationType.CRAWL_COMPLETE in prefs.enabled_types

    def test_should_notify(self):
        prefs = NotificationPreferences()
        assert prefs.should_notify(NotificationType.ITEM_SAVED) is True

    def test_should_notify_disabled(self):
        prefs = NotificationPreferences()
        prefs.enabled = False
        assert prefs.should_notify(NotificationType.ITEM_SAVED) is False

    def test_should_notify_type_disabled(self):
        prefs = NotificationPreferences()
        prefs.disable_type(NotificationType.CRAWL_COMPLETE)
        assert prefs.should_notify(NotificationType.CRAWL_COMPLETE) is False

    def test_to_dict(self):
        prefs = NotificationPreferences()
        d = prefs.to_dict()
        assert d["enabled"] is True


class TestNotificationStore:
    """Tests for NotificationStore."""

    def test_add_notification(self):
        store = NotificationStore()
        notif = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM,
        )
        store.add(notif)
        assert len(store.list_all()) == 1

    def test_get_notification(self):
        store = NotificationStore()
        notif = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM,
        )
        store.add(notif)
        retrieved = store.get(notif.id)
        assert retrieved is not None
        assert retrieved.title == "Test"

    def test_get_notification_not_found(self):
        store = NotificationStore()
        assert store.get("nonexistent") is None

    def test_list_unread(self):
        store = NotificationStore()
        n1 = Notification(
            title="Unread",
            message="Unread",
            notification_type=NotificationType.SYSTEM,
        )
        n2 = Notification(
            title="Read",
            message="Read",
            notification_type=NotificationType.SYSTEM,
        )
        n2.mark_read()
        store.add(n1)
        store.add(n2)
        unread = store.list_unread()
        assert len(unread) == 1
        assert unread[0].title == "Unread"

    def test_list_by_type(self):
        store = NotificationStore()
        store.add(Notification(
            title="Saved",
            message="Item saved",
            notification_type=NotificationType.ITEM_SAVED,
        ))
        store.add(Notification(
            title="Error",
            message="Error",
            notification_type=NotificationType.CRAWL_ERROR,
        ))
        saved = store.list_by_type(NotificationType.ITEM_SAVED)
        assert len(saved) == 1
        assert saved[0].title == "Saved"

    def test_mark_read(self):
        store = NotificationStore()
        notif = Notification(
            title="Test",
            message="Test",
            notification_type=NotificationType.SYSTEM,
        )
        store.add(notif)
        store.mark_read(notif.id)
        assert store.get(notif.id).read is True

    def test_mark_all_read(self):
        store = NotificationStore()
        store.add(Notification(
            title="N1",
            message="N1",
            notification_type=NotificationType.SYSTEM,
        ))
        store.add(Notification(
            title="N2",
            message="N2",
            notification_type=NotificationType.SYSTEM,
        ))
        store.mark_all_read()
        assert store.unread_count == 0

    def test_delete_notification(self):
        store = NotificationStore()
        notif = Notification(
            title="Test",
            message="Test",
            notification_type=NotificationType.SYSTEM,
        )
        store.add(notif)
        store.delete(notif.id)
        assert store.get(notif.id) is None

    def test_unread_count(self):
        store = NotificationStore()
        store.add(Notification(
            title="N1",
            message="N1",
            notification_type=NotificationType.SYSTEM,
        ))
        n2 = Notification(
            title="N2",
            message="N2",
            notification_type=NotificationType.SYSTEM,
        )
        n2.mark_read()
        store.add(n2)
        assert store.unread_count == 1

    def test_total_count(self):
        store = NotificationStore()
        store.add(Notification(
            title="N1",
            message="N1",
            notification_type=NotificationType.SYSTEM,
        ))
        store.add(Notification(
            title="N2",
            message="N2",
            notification_type=NotificationType.SYSTEM,
        ))
        assert store.total_count == 2

    def test_cleanup_expired(self):
        store = NotificationStore()
        past = datetime.now(timezone.utc) - timedelta(days=31)
        store.add(Notification(
            title="Expired",
            message="Expired",
            notification_type=NotificationType.SYSTEM,
            created_at=past,
            ttl_days=30,
        ))
        store.add(Notification(
            title="Active",
            message="Active",
            notification_type=NotificationType.SYSTEM,
        ))
        store.cleanup_expired()
        assert store.total_count == 1

    def test_filter_notifications(self):
        store = NotificationStore()
        store.add(Notification(
            title="Saved",
            message="Item saved",
            notification_type=NotificationType.ITEM_SAVED,
            level=NotificationLevel.INFO,
        ))
        store.add(Notification(
            title="Error",
            message="Error",
            notification_type=NotificationType.CRAWL_ERROR,
            level=NotificationLevel.ERROR,
        ))
        filter_ = NotificationFilter(levels=[NotificationLevel.ERROR])
        results = store.filter(filter_)
        assert len(results) == 1
        assert results[0].title == "Error"

    def test_preferences(self):
        store = NotificationStore()
        prefs = store.get_preferences()
        assert prefs.enabled is True
        store.set_preferences(prefs)
