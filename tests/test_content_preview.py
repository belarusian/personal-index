"""Tests for content_preview module - generate preview thumbnails."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from personal_index.content_preview import (
    Preview,
    PreviewManager,
    PreviewType,
    PreviewStatus,
)


class TestPreview:
    """Tests for Preview dataclass."""

    def test_create_preview_basic(self):
        p = Preview(url="https://example.com/page")
        assert p.url == "https://example.com/page"
        assert p.preview_id is not None
        assert p.preview_type == PreviewType.TEXT
        assert p.status == PreviewStatus.READY
        assert p.created_at is not None

    def test_create_preview_with_title(self):
        p = Preview(url="https://example.com/page", title="My Page")
        assert p.title == "My Page"

    def test_create_preview_with_description(self):
        p = Preview(
            url="https://example.com/page",
            description="A test page",
        )
        assert p.description == "A test page"

    def test_create_preview_image_type(self):
        p = Preview(
            url="https://example.com/page",
            preview_type=PreviewType.IMAGE,
        )
        assert p.preview_type == PreviewType.IMAGE

    def test_create_preview_card_type(self):
        p = Preview(
            url="https://example.com/page",
            preview_type=PreviewType.CARD,
        )
        assert p.preview_type == PreviewType.CARD

    def test_create_preview_video_type(self):
        p = Preview(
            url="https://example.com/page",
            preview_type=PreviewType.VIDEO,
        )
        assert p.preview_type == PreviewType.VIDEO

    def test_create_preview_with_image_url(self):
        p = Preview(
            url="https://example.com/page",
            image_url="https://example.com/thumb.jpg",
        )
        assert p.image_url == "https://example.com/thumb.jpg"

    def test_create_preview_pending(self):
        p = Preview(
            url="https://example.com/page",
            status=PreviewStatus.PENDING,
        )
        assert p.status == PreviewStatus.PENDING

    def test_create_preview_failed(self):
        p = Preview(
            url="https://example.com/page",
            status=PreviewStatus.FAILED,
            error="Timeout",
        )
        assert p.status == PreviewStatus.FAILED
        assert p.error == "Timeout"

    def test_create_preview_with_dimensions(self):
        p = Preview(
            url="https://example.com/page",
            width=800,
            height=600,
        )
        assert p.width == 800
        assert p.height == 600

    def test_preview_to_dict(self):
        p = Preview(
            url="https://example.com/page",
            title="Test",
            description="Desc",
            preview_type=PreviewType.IMAGE,
            image_url="https://example.com/img.jpg",
        )
        d = p.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["title"] == "Test"
        assert d["preview_type"] == "image"
        assert d["image_url"] == "https://example.com/img.jpg"

    def test_preview_from_dict(self):
        data = {
            "preview_id": "p1",
            "url": "https://example.com/page",
            "title": "Test Page",
            "description": "A test",
            "preview_type": "card",
            "image_url": "https://example.com/card.png",
            "status": "ready",
            "width": 600,
            "height": 400,
            "created_at": "2024-01-01T00:00:00+00:00",
        }
        p = Preview.from_dict(data)
        assert p.preview_id == "p1"
        assert p.preview_type == PreviewType.CARD
        assert p.width == 600
        assert p.height == 400

    def test_preview_from_dict_defaults(self):
        data = {"url": "https://example.com/minimal"}
        p = Preview.from_dict(data)
        assert p.preview_type == PreviewType.TEXT
        assert p.status == PreviewStatus.READY
        assert p.title == ""

    def test_preview_is_ready(self):
        p = Preview(url="https://example.com/page")
        assert p.is_ready() is True

    def test_preview_is_ready_pending(self):
        p = Preview(url="https://example.com/page", status=PreviewStatus.PENDING)
        assert p.is_ready() is False

    def test_preview_is_ready_failed(self):
        p = Preview(url="https://example.com/page", status=PreviewStatus.FAILED)
        assert p.is_ready() is False

    def test_preview_generate_text_preview(self):
        p = Preview(
            url="https://example.com/page",
            description="This is a longer description that should be truncated",
        )
        preview = p.generate_text_preview(max_length=20)
        assert len(preview) <= 20

    def test_preview_generate_text_preview_short(self):
        p = Preview(
            url="https://example.com/page",
            description="Short",
        )
        preview = p.generate_text_preview(max_length=100)
        assert preview == "Short"

    def test_preview_generate_text_preview_no_description(self):
        p = Preview(url="https://example.com/page")
        preview = p.generate_text_preview(max_length=100)
        assert preview == ""

    def test_preview_get_favicon_url(self):
        p = Preview(url="https://example.com/page")
        favicon = p.get_favicon_url()
        assert "example.com" in favicon

    def test_preview_get_og_image(self):
        p = Preview(
            url="https://example.com/page",
            image_url="https://example.com/og.jpg",
        )
        assert p.get_og_image() == "https://example.com/og.jpg"

    def test_preview_get_og_image_none(self):
        p = Preview(url="https://example.com/page")
        assert p.get_og_image() is None

    def test_preview_update_status(self):
        p = Preview(url="https://example.com/page", status=PreviewStatus.PENDING)
        p.update_status(PreviewStatus.READY)
        assert p.status == PreviewStatus.READY

    def test_preview_update_error(self):
        p = Preview(url="https://example.com/page")
        p.update_error("Something went wrong")
        assert p.status == PreviewStatus.FAILED
        assert p.error == "Something went wrong"

    def test_preview_is_expired(self):
        from datetime import timedelta
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        p = Preview(url="https://example.com/page", created_at=old, ttl_hours=24)
        assert p.is_expired() is True

    def test_preview_is_not_expired(self):
        from datetime import timedelta
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        p = Preview(url="https://example.com/page", created_at=recent, ttl_hours=24)
        assert p.is_expired() is False

    def test_preview_is_not_expired_no_ttl(self):
        p = Preview(url="https://example.com/page")
        assert p.is_expired() is False


class TestPreviewManager:
    """Tests for PreviewManager class."""

    def test_create_preview(self):
        mgr = PreviewManager()
        pid = mgr.create_preview("https://example.com/page")
        preview = mgr.get_preview(pid)
        assert preview is not None
        assert preview.url == "https://example.com/page"

    def test_create_preview_with_details(self):
        mgr = PreviewManager()
        pid = mgr.create_preview(
            "https://example.com/page",
            title="Test Page",
            description="A test page",
            preview_type=PreviewType.CARD,
        )
        preview = mgr.get_preview(pid)
        assert preview.title == "Test Page"
        assert preview.preview_type == PreviewType.CARD

    def test_create_preview_pending(self):
        mgr = PreviewManager()
        pid = mgr.create_preview(
            "https://example.com/page",
            status=PreviewStatus.PENDING,
        )
        preview = mgr.get_preview(pid)
        assert preview.status == PreviewStatus.PENDING

    def test_get_preview_not_found(self):
        mgr = PreviewManager()
        assert mgr.get_preview("nonexistent") is None

    def test_get_preview_by_url(self):
        mgr = PreviewManager()
        pid = mgr.create_preview("https://example.com/page")
        preview = mgr.get_preview_by_url("https://example.com/page")
        assert preview is not None
        assert preview.preview_id == pid

    def test_list_previews(self):
        mgr = PreviewManager()
        mgr.create_preview("https://example.com/a")
        mgr.create_preview("https://example.com/b")
        previews = mgr.list_previews()
        assert len(previews) == 2

    def test_list_previews_by_type(self):
        mgr = PreviewManager()
        mgr.create_preview("https://example.com/a", preview_type=PreviewType.IMAGE)
        mgr.create_preview("https://example.com/b", preview_type=PreviewType.TEXT)
        mgr.create_preview("https://example.com/c", preview_type=PreviewType.IMAGE)
        images = mgr.list_previews(preview_type=PreviewType.IMAGE)
        assert len(images) == 2

    def test_list_previews_ready(self):
        mgr = PreviewManager()
        mgr.create_preview("https://example.com/a", status=PreviewStatus.READY)
        mgr.create_preview("https://example.com/b", status=PreviewStatus.PENDING)
        ready = mgr.list_previews(status=PreviewStatus.READY)
        assert len(ready) == 1

    def test_list_previews_by_domain(self):
        mgr = PreviewManager()
        mgr.create_preview("https://example.com/a")
        mgr.create_preview("https://example.com/b")
        mgr.create_preview("https://other.com/c")
        domain_previews = mgr.list_previews(domain="example.com")
        assert len(domain_previews) == 2

    def test_update_preview(self):
        mgr = PreviewManager()
        pid = mgr.create_preview("https://example.com/page")
        mgr.update_preview(pid, title="Updated Title")
        preview = mgr.get_preview(pid)
        assert preview.title == "Updated Title"

    def test_update_preview_image_url(self):
        mgr = PreviewManager()
        pid = mgr.create_preview("https://example.com/page")
        mgr.update_preview(pid, image_url="https://example.com/new.jpg")
        preview = mgr.get_preview(pid)
        assert preview.image_url == "https://example.com/new.jpg"

    def test_update_preview_not_found(self):
        mgr = PreviewManager()
        mgr.update_preview("nonexistent", title="Nope")
        # Should not raise

    def test_delete_preview(self):
        mgr = PreviewManager()
        pid = mgr.create_preview("https://example.com/page")
        result = mgr.delete_preview(pid)
        assert result is True
        assert mgr.get_preview(pid) is None

    def test_delete_preview_not_found(self):
        mgr = PreviewManager()
        result = mgr.delete_preview("nonexistent")
        assert result is False

    def test_get_preview_count(self):
        mgr = PreviewManager()
        assert mgr.get_preview_count() == 0
        mgr.create_preview("https://example.com/a")
        mgr.create_preview("https://example.com/b")
        assert mgr.get_preview_count() == 2

    def test_get_pending_previews(self):
        mgr = PreviewManager()
        mgr.create_preview("https://example.com/a", status=PreviewStatus.PENDING)
        mgr.create_preview("https://example.com/b", status=PreviewStatus.READY)
        mgr.create_preview("https://example.com/c", status=PreviewStatus.PENDING)
        pending = mgr.get_pending_previews()
        assert len(pending) == 2

    def test_get_expired_previews(self):
        from datetime import timedelta
        mgr = PreviewManager()
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        mgr.create_preview("https://example.com/a", created_at=old, ttl_hours=24)
        mgr.create_preview("https://example.com/b")
        expired = mgr.get_expired_previews()
        assert len(expired) == 1

    def test_generate_text_preview(self):
        mgr = PreviewManager()
        pid = mgr.create_preview(
            "https://example.com/page",
            description="This is a test description",
        )
        text = mgr.generate_text_preview(pid, max_length=10)
        assert len(text) <= 10

    def test_generate_text_preview_not_found(self):
        mgr = PreviewManager()
        text = mgr.generate_text_preview("nonexistent")
        assert text == ""

    def test_generate_batch_previews(self):
        mgr = PreviewManager()
        urls = [
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        ]
        ids = mgr.generate_batch_previews(urls)
        assert len(ids) == 3
        for pid in ids:
            preview = mgr.get_preview(pid)
            assert preview is not None
            assert preview.status == PreviewStatus.PENDING

    def test_mark_preview_ready(self):
        mgr = PreviewManager()
        pid = mgr.create_preview(
            "https://example.com/page",
            status=PreviewStatus.PENDING,
        )
        mgr.mark_preview_ready(pid, image_url="https://example.com/thumb.jpg")
        preview = mgr.get_preview(pid)
        assert preview.status == PreviewStatus.READY
        assert preview.image_url == "https://example.com/thumb.jpg"

    def test_mark_preview_failed(self):
        mgr = PreviewManager()
        pid = mgr.create_preview(
            "https://example.com/page",
            status=PreviewStatus.PENDING,
        )
        mgr.mark_preview_failed(pid, error="Timeout")
        preview = mgr.get_preview(pid)
        assert preview.status == PreviewStatus.FAILED
        assert preview.error == "Timeout"

    def test_refresh_preview(self):
        mgr = PreviewManager()
        pid = mgr.create_preview("https://example.com/page")
        new_pid = mgr.refresh_preview(pid)
        assert new_pid != pid
        new_preview = mgr.get_preview(new_pid)
        assert new_preview is not None
        assert new_preview.url == "https://example.com/page"

    def test_cleanup_expired(self):
        from datetime import timedelta
        mgr = PreviewManager()
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        mgr.create_preview("https://example.com/a", created_at=old, ttl_hours=24)
        mgr.create_preview("https://example.com/b", created_at=old, ttl_hours=24)
        mgr.create_preview("https://example.com/c")
        removed = mgr.cleanup_expired()
        assert removed == 2
        assert mgr.get_preview_count() == 1

    def test_get_previews_for_urls(self):
        mgr = PreviewManager()
        mgr.create_preview("https://example.com/a")
        mgr.create_preview("https://example.com/b")
        mgr.create_preview("https://other.com/c")
        previews = mgr.get_previews_for_urls([
            "https://example.com/a",
            "https://other.com/c",
        ])
        assert len(previews) == 2

    def test_serialize_deserialize(self):
        mgr = PreviewManager()
        pid = mgr.create_preview(
            "https://example.com/page",
            title="Test",
            preview_type=PreviewType.CARD,
        )
        data = mgr.to_dict()
        new_mgr = PreviewManager.from_dict(data)
        preview = new_mgr.get_preview(pid)
        assert preview is not None
        assert preview.title == "Test"
        assert preview.preview_type == PreviewType.CARD

    def test_get_preview_summary(self):
        mgr = PreviewManager()
        mgr.create_preview("https://example.com/a", status=PreviewStatus.READY)
        mgr.create_preview("https://example.com/b", status=PreviewStatus.PENDING)
        mgr.create_preview("https://example.com/c", status=PreviewStatus.FAILED)
        summary = mgr.get_preview_summary()
        assert summary["total"] == 3
        assert summary["ready"] == 1
        assert summary["pending"] == 1
        assert summary["failed"] == 1
