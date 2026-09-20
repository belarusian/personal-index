"""Adversarial deep tests for personal_index.notifications.

Cycle 306 - VALIDATOR probe of notifications.py (never deep-probed).

Contract pinned from module docstrings and public API:
- Notification dataclass: default timestamp (UTC ISO), default notification_id
  (unique per instance), to_dict/from_dict round-trip.
- NotificationLevel/NotificationType enums: value access.
- ConsoleHandler: handle() returns True, close() no-op.
- FileHandler: handle() appends JSON line, close() flushes.
- InMemoryHandler: handle() stores, get_all() returns all, get_unread() filters,
  mark_all_read() stamps read_at, clear() returns count.
- NotificationManager: add_handler/remove_handler, notify() routes to all
  handlers, notify_* convenience methods build correct NotificationType.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

from personal_index.notifications import (
    ConsoleHandler,
    FileHandler,
    InMemoryHandler,
    Notification,
    NotificationLevel,
    NotificationManager,
    NotificationType,
)


class TestNotificationDataclass:
    """Notification dataclass defaults and serialization."""

    def test_default_timestamp_is_utc_iso(self):
        n = Notification(notification_type="test", title="t")
        assert n.timestamp
        # Parse to verify it's valid ISO
        datetime.fromisoformat(n.timestamp)

    def test_default_notification_id_unique(self):
        n1 = Notification(notification_type="test", title="t")
        n2 = Notification(notification_type="test", title="t")
        assert n1.notification_id != n2.notification_id

    def test_custom_id_preserved(self):
        n = Notification(notification_id="custom-123", notification_type="test", title="t")
        assert n.notification_id == "custom-123"

    def test_to_dict_keys(self):
        n = Notification(notification_type="test", title="t", message="m")
        d = n.to_dict()
        assert "notification_id" in d
        assert "notification_type" in d
        assert "title" in d
        assert "message" in d
        assert "timestamp" in d
        assert "level" in d
        assert "read" in d
        assert "read_at" in d
        assert "metadata" in d

    def test_from_dict_roundtrip(self):
        n = Notification(notification_type="test", title="t", message="m", level="warning")
        d = n.to_dict()
        n2 = Notification.from_dict(d)
        assert n2.notification_type == "test"
        assert n2.title == "t"
        assert n2.message == "m"
        assert n2.level == "warning"

    def test_from_dict_empty_dict(self):
        n = Notification.from_dict({})
        assert n.notification_id  # auto-generated
        assert n.timestamp  # auto-generated

    def test_from_dict_with_none_values(self):
        d = {"notification_type": None, "title": None, "message": None}
        n = Notification.from_dict(d)
        assert n.notification_type is None
        assert n.title is None
        assert n.message is None

    def test_unicode_roundtrip(self):
        n = Notification(notification_type="test", title="日本語", message="🚀")
        d = n.to_dict()
        n2 = Notification.from_dict(d)
        assert n2.title == "日本語"
        assert n2.message == "🚀"

    def test_empty_string_fields(self):
        n = Notification(notification_type="", title="", message="")
        assert n.notification_type == ""
        assert n.title == ""
        assert n.message == ""

    def test_metadata_dict_preserved(self):
        meta = {"key": "value", "num": 42}
        n = Notification(notification_type="test", title="t", metadata=meta)
        d = n.to_dict()
        assert d["metadata"] == meta

    def test_default_metadata_is_dict(self):
        n = Notification(notification_type="test", title="t")
        assert isinstance(n.metadata, dict)
        assert n.metadata == {}


class TestEnums:
    """NotificationLevel and NotificationType enum values."""

    def test_level_values(self):
        assert NotificationLevel.INFO.value == "info"
        assert NotificationLevel.WARNING.value == "warning"
        assert NotificationLevel.ERROR.value == "error"
        assert NotificationLevel.CRITICAL.value == "critical"

    def test_type_values(self):
        assert NotificationType.CRAWL_COMPLETE.value == "crawl_complete"
        assert NotificationType.SEARCH_HIT.value == "search_hit"
        assert NotificationType.NEW_CONTENT.value == "new_content"


class TestConsoleHandler:
    """ConsoleHandler basic contract."""

    def test_handle_returns_true(self):
        h = ConsoleHandler(colors=False)
        n = Notification(notification_type="test", title="t")
        assert h.handle(n) is True

    def test_close_noop(self):
        h = ConsoleHandler()
        h.close()  # should not raise


class TestFileHandler:
    """FileHandler writes JSON lines."""

    def test_handle_appends_json_line(self, tmp_path):
        f = tmp_path / "notifs.log"
        h = FileHandler(str(f))
        n = Notification(notification_type="test", title="t", message="m")
        assert h.handle(n) is True
        h.close()
        lines = f.read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["title"] == "t"
        assert parsed["message"] == "m"

    def test_multiple_notifications(self, tmp_path):
        f = tmp_path / "notifs.log"
        h = FileHandler(str(f))
        for i in range(3):
            n = Notification(notification_type="test", title=f"t{i}")
            h.handle(n)
        h.close()
        lines = f.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_close_flushes(self, tmp_path):
        f = tmp_path / "notifs.log"
        h = FileHandler(str(f))
        n = Notification(notification_type="test", title="t")
        h.handle(n)
        # File may not be flushed yet
        h.close()
        assert f.exists()
        assert f.read_text().strip() != ""


class TestInMemoryHandler:
    """InMemoryHandler storage and filtering."""

    def test_handle_stores_notification(self):
        h = InMemoryHandler()
        n = Notification(notification_type="test", title="t")
        h.handle(n)
        assert len(h.get_all()) == 1

    def test_get_unread_filters_read(self):
        h = InMemoryHandler()
        n1 = Notification(notification_type="test", title="t1")
        n2 = Notification(notification_type="test", title="t2")
        h.handle(n1)
        h.handle(n2)
        assert len(h.get_unread()) == 2
        h.mark_all_read()
        assert len(h.get_unread()) == 0

    def test_mark_all_read_stamps_read_at(self):
        h = InMemoryHandler()
        n = Notification(notification_type="test", title="t")
        h.handle(n)
        assert n.read_at is None
        h.mark_all_read()
        assert n.read_at is not None

    def test_clear_returns_count(self):
        h = InMemoryHandler()
        for i in range(5):
            h.handle(Notification(notification_type="test", title=f"t{i}"))
        assert h.clear() == 5
        assert len(h.get_all()) == 0

    def test_clear_idempotent(self):
        h = InMemoryHandler()
        h.handle(Notification(notification_type="test", title="t"))
        assert h.clear() == 1
        assert h.clear() == 0

    def test_max_size_eviction(self):
        h = InMemoryHandler(max_size=3)
        for i in range(5):
            h.handle(Notification(notification_type="test", title=f"t{i}"))
        assert len(h.get_all()) == 3
        # Oldest should be evicted
        titles = [n.title for n in h.get_all()]
        assert "t0" not in titles
        assert "t4" in titles


class TestNotificationManager:
    """NotificationManager routing."""

    def test_add_and_remove_handler(self):
        mgr = NotificationManager()
        h = ConsoleHandler()
        mgr.add_handler(h)
        assert mgr.remove_handler(h) is True
        assert mgr.remove_handler(h) is False

    def test_notify_routes_to_all_handlers(self):
        mgr = NotificationManager()
        h1 = InMemoryHandler()
        h2 = InMemoryHandler()
        mgr.add_handler(h1)
        mgr.add_handler(h2)
        n = Notification(notification_type="test", title="t")
        mgr.notify(n)
        assert len(h1.get_all()) == 1
        assert len(h2.get_all()) == 1

    def test_notify_crawl_complete_type(self):
        mgr = NotificationManager()
        h = InMemoryHandler()
        mgr.add_handler(h)
        mgr.notify_crawl_complete("http://example.com", 10, 1.5)
        n = h.get_all()[0]
        assert n.notification_type == NotificationType.CRAWL_COMPLETE.value

    def test_notify_crawl_error_type(self):
        mgr = NotificationManager()
        h = InMemoryHandler()
        mgr.add_handler(h)
        mgr.notify_crawl_error("http://example.com", "timeout")
        n = h.get_all()[0]
        assert n.notification_type == NotificationType.CRAWL_ERROR.value

    def test_notify_new_content_type(self):
        mgr = NotificationManager()
        h = InMemoryHandler()
        mgr.add_handler(h)
        mgr.notify_new_content("http://example.com", "Title", ["tech"])
        n = h.get_all()[0]
        assert n.notification_type == NotificationType.NEW_CONTENT.value

    def test_notify_interest_match_type(self):
        mgr = NotificationManager()
        h = InMemoryHandler()
        mgr.add_handler(h)
        mgr.notify_interest_match("http://example.com", "tech", 0.9)
        n = h.get_all()[0]
        assert n.notification_type == NotificationType.INTEREST_MATCH.value

    def test_close_closes_all_handlers(self):
        mgr = NotificationManager()
        h = InMemoryHandler()
        mgr.add_handler(h)
        mgr.close()  # should not raise

    def test_notify_with_no_handlers(self):
        mgr = NotificationManager()
        n = Notification(notification_type="test", title="t")
        count = mgr.notify(n)
        assert count == 0

    def test_unicode_in_notification(self):
        mgr = NotificationManager()
        h = InMemoryHandler()
        mgr.add_handler(h)
        n = Notification(notification_type="test", title="日本語", message="🚀")
        mgr.notify(n)
        stored = h.get_all()[0]
        assert stored.title == "日本語"
        assert stored.message == "🚀"

    def test_empty_title_and_message(self):
        mgr = NotificationManager()
        h = InMemoryHandler()
        mgr.add_handler(h)
        n = Notification(notification_type="test", title="", message="")
        mgr.notify(n)
        stored = h.get_all()[0]
        assert stored.title == ""
        assert stored.message == ""


class TestEdgeCases:
    """Adversarial edge cases."""

    def test_file_handler_nonexistent_dir(self, tmp_path):
        # FileHandler should fail gracefully or raise
        path = str(tmp_path / "nonexistent" / "notifs.log")
        h = FileHandler(path)
        n = Notification(notification_type="test", title="t")
        try:
            h.handle(n)
        except (OSError, FileNotFoundError):
            pass  # acceptable
        finally:
            h.close()

    def test_in_memory_handler_zero_max_size(self):
        h = InMemoryHandler(max_size=0)
        h.handle(Notification(notification_type="test", title="t"))
        # With max_size=0, all notifications are evicted
        assert len(h.get_all()) == 0

    def test_in_memory_handler_negative_max_size(self):
        h = InMemoryHandler(max_size=-1)
        h.handle(Notification(notification_type="test", title="t"))
        # Negative max_size should be treated as unbounded or evict all
        # (implementation detail, just ensure no crash)
        assert isinstance(h.get_all(), list)

    def test_notification_id_format(self):
        n = Notification(notification_type="test", title="t")
        assert n.notification_id.startswith("notif_")
        # Should have timestamp and random component
        parts = n.notification_id.split("_")
        assert len(parts) >= 3  # notif_{timestamp}_{random}
