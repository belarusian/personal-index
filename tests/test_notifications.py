"""Tests for notification system."""

from __future__ import annotations

import json
import logging
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from personal_index.notifications import (
    ConsoleHandler,
    FileHandler,
    InMemoryHandler,
    Notification,
    NotificationLevel,
    NotificationManager,
    NotificationType,
)


class TestNotification:
    """Tests for Notification dataclass."""

    def test_create_notification(self):
        n = Notification(
            notification_type=NotificationType.CRAWL_COMPLETE.value,
            level=NotificationLevel.INFO.value,
            title="Test",
            message="Test message",
        )
        assert n.notification_id
        assert n.timestamp
        assert n.read is False

    def test_to_dict(self):
        n = Notification(title="Test", message="Msg")
        d = n.to_dict()
        assert d["title"] == "Test"
        assert d["message"] == "Msg"
        assert "notification_id" in d

    def test_from_dict(self):
        data = {
            "notification_id": "test_123",
            "notification_type": "crawl_complete",
            "level": "info",
            "title": "Test",
            "message": "Msg",
            "timestamp": "2024-01-01T00:00:00",
            "metadata": {},
            "read": False,
        }
        n = Notification.from_dict(data)
        assert n.notification_id == "test_123"
        assert n.title == "Test"

    def test_defaults(self):
        n = Notification()
        assert n.level == "info"
        assert n.read is False

    def test_custom_metadata(self):
        n = Notification(title="Test", metadata={"key": "value"})
        assert n.metadata["key"] == "value"


class TestInMemoryHandler:
    """Tests for InMemoryHandler."""

    def test_handle_stores_notification(self):
        handler = InMemoryHandler()
        n = Notification(title="Test", message="Msg")
        assert handler.handle(n) is True
        assert len(handler.get_all()) == 1

    def test_get_unread(self):
        handler = InMemoryHandler()
        n1 = Notification(title="Test1")
        n2 = Notification(title="Test2")
        handler.handle(n1)
        handler.handle(n2)
        n1.read = True
        assert len(handler.get_unread()) == 1

    def test_mark_all_read(self):
        handler = InMemoryHandler()
        for i in range(5):
            handler.handle(Notification(title=f"Test{i}"))
        count = handler.mark_all_read()
        assert count == 5
        assert len(handler.get_unread()) == 0

    def test_clear(self):
        handler = InMemoryHandler()
        for i in range(10):
            handler.handle(Notification(title=f"Test{i}"))
        count = handler.clear()
        assert count == 10
        assert len(handler.get_all()) == 0

    def test_max_size(self):
        handler = InMemoryHandler(max_size=3)
        for i in range(5):
            handler.handle(Notification(title=f"Test{i}"))
        assert len(handler.get_all()) == 3

    def test_close_clears(self):
        handler = InMemoryHandler()
        handler.handle(Notification(title="Test"))
        handler.close()
        assert len(handler.get_all()) == 0


class TestFileHandler:
    """Tests for FileHandler."""

    def test_handle_writes_to_file(self, tmp_path):
        filepath = str(tmp_path / "test_notifications.log")
        handler = FileHandler(filepath=filepath)
        n = Notification(title="Test", message="Msg")
        assert handler.handle(n) is True
        assert os.path.exists(filepath)
        with open(filepath) as f:
            data = json.loads(f.readline())
        assert data["title"] == "Test"

    def test_handle_appends(self, tmp_path):
        filepath = str(tmp_path / "test_notifications.log")
        handler = FileHandler(filepath=filepath)
        handler.handle(Notification(title="Test1"))
        handler.handle(Notification(title="Test2"))
        with open(filepath) as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_close(self, tmp_path):
        filepath = str(tmp_path / "test_notifications.log")
        handler = FileHandler(filepath=filepath)
        handler.close()  # Should not raise


class TestConsoleHandler:
    """Tests for ConsoleHandler."""

    def test_handle_returns_true(self, caplog):
        caplog.set_level(logging.INFO)
        handler = ConsoleHandler(colors=False)
        n = Notification(title="Test", message="Msg")
        assert handler.handle(n) is True
        assert "Test" in caplog.text

    def test_close(self):
        handler = ConsoleHandler()
        handler.close()  # Should not raise


class TestNotificationManager:
    """Tests for NotificationManager."""

    def test_add_and_notify(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        manager.notify(Notification(title="Test"))
        assert len(handler.get_all()) == 1

    def test_remove_handler(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        assert manager.remove_handler(handler) is True
        manager.notify(Notification(title="Test"))
        assert len(handler.get_all()) == 0

    def test_remove_nonexistent_handler(self):
        manager = NotificationManager()
        assert manager.remove_handler(InMemoryHandler()) is False

    def test_multiple_handlers(self):
        manager = NotificationManager()
        h1 = InMemoryHandler()
        h2 = InMemoryHandler()
        manager.add_handler(h1)
        manager.add_handler(h2)
        count = manager.notify(Notification(title="Test"))
        assert count == 2
        assert len(h1.get_all()) == 1
        assert len(h2.get_all()) == 1

    def test_filter_allows(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        manager.add_filter(lambda n: n.level == "info")
        manager.notify(Notification(title="Test", level="info"))
        assert len(handler.get_all()) == 1

    def test_filter_blocks(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        manager.add_filter(lambda n: n.level == "info")
        manager.notify(Notification(title="Test", level="error"))
        assert len(handler.get_unread()) == 0

    def test_notify_crawl_complete(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        manager.notify_crawl_complete("http://example.com", 10, 5.5)
        n = handler.get_all()[0]
        assert n.title == "Crawl Complete"
        assert n.metadata["pages_found"] == 10

    def test_notify_crawl_error(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        manager.notify_crawl_error("http://example.com", "timeout")
        n = handler.get_all()[0]
        assert n.level == "error"
        assert n.metadata["error"] == "timeout"

    def test_notify_new_content(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        manager.notify_new_content("http://example.com", "Test Page", ["python"])
        n = handler.get_all()[0]
        assert n.title == "New Content Found"
        assert n.metadata["matched_interests"] == ["python"]

    def test_notify_interest_match(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        manager.notify_interest_match("http://example.com", "python", 0.95)
        n = handler.get_all()[0]
        assert n.title == "Interest Match"
        assert n.metadata["score"] == 0.95

    def test_close(self):
        manager = NotificationManager()
        handler = InMemoryHandler()
        manager.add_handler(handler)
        manager.close()
        assert len(manager._handlers) == 0

    def test_handler_failure_doesnt_crash(self):
        manager = NotificationManager()
        bad_handler = MagicMock()
        bad_handler.handle.side_effect = Exception("boom")
        good_handler = InMemoryHandler()
        manager.add_handler(bad_handler)
        manager.add_handler(good_handler)
        count = manager.notify(Notification(title="Test"))
        assert count == 1  # Only good handler succeeded
