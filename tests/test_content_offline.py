"""Tests for content_offline module - offline access to saved content."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_offline import (
    OfflineContentItem,
    OfflineStore,
    OfflineStatus,
    OfflinePriority,
)


class TestOfflineContentItem:
    """Tests for OfflineContentItem dataclass."""

    def test_create_offline_item_basic(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test Article",
        )
        assert item.url == "https://example.com/article"
        assert item.title == "Test Article"
        assert item.item_id is not None
        assert item.status == OfflineStatus.AVAILABLE
        assert item.content is None
        assert item.created_at is not None

    def test_create_offline_item_with_content(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test Article",
            content="<html><body>Hello</body></html>",
        )
        assert item.content == "<html><body>Hello</body></html>"
        assert item.content_length == len("<html><body>Hello</body></html>")

    def test_create_offline_item_with_metadata(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            author="John Doe",
            published_at="2024-01-01T00:00:00+00:00",
            tags=["tech", "news"],
        )
        assert item.author == "John Doe"
        assert item.published_at == "2024-01-01T00:00:00+00:00"
        assert item.tags == ["tech", "news"]

    def test_create_offline_item_pending(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            status=OfflineStatus.PENDING,
        )
        assert item.status == OfflineStatus.PENDING

    def test_create_offline_item_failed(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            status=OfflineStatus.FAILED,
            error="Network error",
        )
        assert item.status == OfflineStatus.FAILED
        assert item.error == "Network error"

    def test_create_offline_item_expired(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            status=OfflineStatus.EXPIRED,
        )
        assert item.status == OfflineStatus.EXPIRED

    def test_offline_item_to_dict(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            content="<html>test</html>",
            tags=["tech"],
        )
        d = item.to_dict()
        assert d["url"] == "https://example.com/article"
        assert d["title"] == "Test"
        assert d["content"] == "<html>test</html>"
        assert d["tags"] == ["tech"]
        assert d["content_length"] == 17
        assert d["status"] == "available"

    def test_offline_item_from_dict(self):
        data = {
            "item_id": "abc123",
            "url": "https://example.com/article",
            "title": "Test Article",
            "content": "<html>test</html>",
            "author": "Jane",
            "published_at": "2024-01-01T00:00:00+00:00",
            "tags": ["tech"],
            "status": "available",
            "priority": "normal",
            "content_length": 13,
            "expires_at": "2024-12-31T00:00:00+00:00",
            "last_accessed_at": "2024-06-01T00:00:00+00:00",
            "created_at": "2024-01-01T00:00:00+00:00",
            "error": None,
        }
        item = OfflineContentItem.from_dict(data)
        assert item.item_id == "abc123"
        assert item.url == "https://example.com/article"
        assert item.title == "Test Article"
        assert item.content == "<html>test</html>"
        assert item.author == "Jane"
        assert item.tags == ["tech"]
        assert item.status == OfflineStatus.AVAILABLE
        assert item.expires_at == "2024-12-31T00:00:00+00:00"

    def test_offline_item_from_dict_minimal(self):
        data = {
            "url": "https://example.com/minimal",
        }
        item = OfflineContentItem.from_dict(data)
        assert item.url == "https://example.com/minimal"
        assert item.status == OfflineStatus.AVAILABLE
        assert item.content is None

    def test_offline_item_mark_available(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            status=OfflineStatus.PENDING,
        )
        item.mark_available("<html>content</html>")
        assert item.status == OfflineStatus.AVAILABLE
        assert item.content == "<html>content</html>"

    def test_offline_item_mark_failed(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            status=OfflineStatus.PENDING,
        )
        item.mark_failed("Connection timeout")
        assert item.status == OfflineStatus.FAILED
        assert item.error == "Connection timeout"

    def test_offline_item_mark_expired(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            status=OfflineStatus.AVAILABLE,
        )
        item.mark_expired()
        assert item.status == OfflineStatus.EXPIRED

    def test_offline_item_mark_pending(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            status=OfflineStatus.EXPIRED,
        )
        item.mark_pending()
        assert item.status == OfflineStatus.PENDING
        assert item.content is None

    def test_offline_item_record_access(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        item.record_access()
        assert item.last_accessed_at is not None
        assert item.access_count == 1
        item.record_access()
        assert item.access_count == 2

    def test_offline_item_add_tag(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        item.add_tag("tech")
        assert "tech" in item.tags
        item.add_tag("tech")
        assert item.tags.count("tech") == 1

    def test_offline_item_remove_tag(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            tags=["tech", "news"],
        )
        item.remove_tag("tech")
        assert "tech" not in item.tags
        assert "news" in item.tags

    def test_offline_item_is_expired(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            expires_at=past,
        )
        assert item.is_expired() is True

    def test_offline_item_is_not_expired(self):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            expires_at=future,
        )
        assert item.is_expired() is False

    def test_offline_item_is_not_expired_no_expiry(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        assert item.is_expired() is False

    def test_offline_item_set_expiry(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        item.set_expiry_days(30)
        assert item.expires_at is not None

    def test_offline_item_get_preview(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
            content="<html><body>This is a long article content here</body></html>",
        )
        preview = item.get_preview(20)
        assert len(preview) <= 20

    def test_offline_item_get_preview_no_content(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        preview = item.get_preview(20)
        assert preview == ""

    def test_offline_item_update_content(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        item.update_content("<html>new content</html>")
        assert item.content == "<html>new content</html>"
        assert item.content_length == 24

    def test_offline_item_update_metadata(self):
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Old Title",
        )
        item.update_metadata(title="New Title", author="New Author")
        assert item.title == "New Title"
        assert item.author == "New Author"


class TestOfflineStore:
    """Tests for OfflineStore class."""

    def test_create_store(self):
        store = OfflineStore()
        assert store.name == "default"
        assert len(store.items) == 0

    def test_create_store_with_name(self):
        store = OfflineStore(name="my-store")
        assert store.name == "my-store"

    def test_add_item(self):
        store = OfflineStore()
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        store.add_item(item)
        assert len(store.items) == 1
        assert store.get_item(item.item_id) == item

    def test_add_duplicate_url(self):
        store = OfflineStore()
        item1 = OfflineContentItem(
            url="https://example.com/article",
            title="Test 1",
        )
        item2 = OfflineContentItem(
            url="https://example.com/article",
            title="Test 2",
        )
        store.add_item(item1)
        store.add_item(item2)
        assert len(store.items) == 1
        assert store.get_item(item1.item_id) == item1

    def test_remove_item(self):
        store = OfflineStore()
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        store.add_item(item)
        store.remove_item(item.item_id)
        assert len(store.items) == 0

    def test_remove_nonexistent_item(self):
        store = OfflineStore()
        store.remove_item("nonexistent")
        assert len(store.items) == 0

    def test_get_item_by_url(self):
        store = OfflineStore()
        item = OfflineContentItem(
            url="https://example.com/article",
            title="Test",
        )
        store.add_item(item)
        found = store.get_item_by_url("https://example.com/article")
        assert found == item

    def test_get_item_by_url_not_found(self):
        store = OfflineStore()
        found = store.get_item_by_url("https://example.com/notfound")
        assert found is None

    def test_get_available_items(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", status=OfflineStatus.AVAILABLE
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B", status=OfflineStatus.PENDING
        ))
        available = store.get_available_items()
        assert len(available) == 1
        assert available[0].url == "https://example.com/a"

    def test_get_pending_items(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", status=OfflineStatus.PENDING
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B", status=OfflineStatus.AVAILABLE
        ))
        pending = store.get_pending_items()
        assert len(pending) == 1
        assert pending[0].url == "https://example.com/a"

    def test_get_failed_items(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", status=OfflineStatus.FAILED
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B", status=OfflineStatus.AVAILABLE
        ))
        failed = store.get_failed_items()
        assert len(failed) == 1
        assert failed[0].url == "https://example.com/a"

    def test_get_expired_items(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", expires_at=past
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B", status=OfflineStatus.AVAILABLE
        ))
        expired = store.get_expired_items()
        assert len(expired) == 1

    def test_search_items_by_title(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="Python Tutorial"
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="JavaScript Guide"
        ))
        results = store.search("Python")
        assert len(results) == 1
        assert results[0].title == "Python Tutorial"

    def test_search_items_by_tags(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", tags=["tech"]
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B", tags=["news"]
        ))
        results = store.search_by_tag("tech")
        assert len(results) == 1

    def test_search_items_empty(self):
        store = OfflineStore()
        results = store.search("nonexistent")
        assert len(results) == 0

    def test_set_max_items(self):
        store = OfflineStore(max_items=3)
        for i in range(5):
            store.add_item(OfflineContentItem(
                url=f"https://example.com/{i}", title=f"Item {i}"
            ))
        assert len(store.items) <= 3

    def test_set_max_storage_bytes(self):
        store = OfflineStore(max_storage_bytes=100)
        store.add_item(OfflineContentItem(
            url="https://example.com/big",
            title="Big",
            content="x" * 50,
        ))
        assert len(store.items) == 1

    def test_evict_expired(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/expired", title="Expired", expires_at=past
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/valid", title="Valid"
        ))
        store.evict_expired()
        assert len(store.items) == 1
        assert store.items[0].url == "https://example.com/valid"

    def test_evict_least_accessed(self):
        store = OfflineStore(max_items=2)
        item1 = OfflineContentItem(url="https://example.com/a", title="A")
        item1.record_access()
        item1.record_access()
        item2 = OfflineContentItem(url="https://example.com/b", title="B")
        item3 = OfflineContentItem(url="https://example.com/c", title="C")
        store.add_item(item1)
        store.add_item(item2)
        store.add_item(item3)
        assert len(store.items) == 2
        assert item1 in store.items

    def test_get_store_stats(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", content="<html>a</html>"
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B", status=OfflineStatus.PENDING
        ))
        stats = store.get_stats()
        assert stats["total"] == 2
        assert stats["available"] == 1
        assert stats["pending"] == 1

    def test_get_store_stats_empty(self):
        store = OfflineStore()
        stats = store.get_stats()
        assert stats["total"] == 0

    def test_to_dict(self):
        store = OfflineStore(name="test-store")
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A"
        ))
        d = store.to_dict()
        assert d["name"] == "test-store"
        assert len(d["items"]) == 1

    def test_from_dict(self):
        data = {
            "name": "restored-store",
            "max_items": 100,
            "max_storage_bytes": 1048576,
            "items": [
                {
                    "item_id": "abc",
                    "url": "https://example.com/a",
                    "title": "A",
                    "content": "<html>a</html>",
                    "status": "available",
                    "tags": [],
                    "created_at": "2024-01-01T00:00:00+00:00",
                }
            ],
        }
        store = OfflineStore.from_dict(data)
        assert store.name == "restored-store"
        assert len(store.items) == 1
        assert store.items[0].title == "A"

    def test_clear_all(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A"
        ))
        store.clear_all()
        assert len(store.items) == 0

    def test_get_total_content_size(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", content="12345"
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B", content="1234567890"
        ))
        size = store.get_total_content_size()
        assert size == 15

    def test_get_total_content_size_no_content(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A"
        ))
        size = store.get_total_content_size()
        assert size == 0

    def test_retry_failed(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", status=OfflineStatus.FAILED
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B", status=OfflineStatus.AVAILABLE
        ))
        store.retry_failed()
        assert len(store.get_pending_items()) == 1

    def test_refresh_expired(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A", expires_at=past
        ))
        store.refresh_expired()
        pending = store.get_pending_items()
        assert len(pending) == 1

    def test_get_items_sorted_by_access(self):
        store = OfflineStore()
        item1 = OfflineContentItem(url="https://example.com/a", title="A")
        item2 = OfflineContentItem(url="https://example.com/b", title="B")
        item1.record_access()
        item1.record_access()
        item1.record_access()
        store.add_item(item1)
        store.add_item(item2)
        sorted_items = store.get_items_sorted_by_access()
        assert sorted_items[0].url == "https://example.com/a"

    def test_get_items_sorted_by_date(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A",
            created_at="2024-01-01T00:00:00+00:00"
        ))
        store.add_item(OfflineContentItem(
            url="https://example.com/b", title="B",
            created_at="2024-06-01T00:00:00+00:00"
        ))
        sorted_items = store.get_items_sorted_by_date()
        assert sorted_items[0].url == "https://example.com/b"

    def test_batch_add(self):
        store = OfflineStore()
        urls = [
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        ]
        store.batch_add(urls, status=OfflineStatus.PENDING)
        assert len(store.items) == 3

    def test_batch_add_with_titles(self):
        store = OfflineStore()
        items = [
            OfflineContentItem(url="https://example.com/a", title="A"),
            OfflineContentItem(url="https://example.com/b", title="B"),
        ]
        store.batch_add(items)
        assert len(store.items) == 2

    def test_contains_url(self):
        store = OfflineStore()
        store.add_item(OfflineContentItem(
            url="https://example.com/a", title="A"
        ))
        assert store.contains_url("https://example.com/a") is True
        assert store.contains_url("https://example.com/b") is False

    def test_update_item_content(self):
        store = OfflineStore()
        item = OfflineContentItem(
            url="https://example.com/a", title="A"
        )
        store.add_item(item)
        store.update_item_content(item.item_id, "<html>updated</html>")
        updated = store.get_item(item.item_id)
        assert updated.content == "<html>updated</html>"

    def test_update_item_tags(self):
        store = OfflineStore()
        item = OfflineContentItem(
            url="https://example.com/a", title="A"
        )
        store.add_item(item)
        store.update_item_tags(item.item_id, ["tech", "new"])
        updated = store.get_item(item.item_id)
        assert updated.tags == ["tech", "new"]


class TestOfflineStatus:
    """Tests for OfflineStatus enum."""

    def test_status_values(self):
        assert OfflineStatus.AVAILABLE.value == "available"
        assert OfflineStatus.PENDING.value == "pending"
        assert OfflineStatus.FAILED.value == "failed"
        assert OfflineStatus.EXPIRED.value == "expired"

    def test_status_from_string(self):
        assert OfflineStatus("available") == OfflineStatus.AVAILABLE
        assert OfflineStatus("pending") == OfflineStatus.PENDING

    def test_status_invalid_string(self):
        with pytest.raises(ValueError):
            OfflineStatus("invalid")


class TestOfflinePriority:
    """Tests for OfflinePriority enum."""

    def test_priority_values(self):
        assert OfflinePriority.HIGH.value == 0
        assert OfflinePriority.NORMAL.value == 1
        assert OfflinePriority.LOW.value == 2

    def test_priority_ordering(self):
        assert OfflinePriority.HIGH < OfflinePriority.NORMAL
        assert OfflinePriority.NORMAL < OfflinePriority.LOW
