"""Tests for content_sharing - generate shareable links."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from personal_index.content_sharing import (
    ShareLink,
    ShareStore,
    ShareFormat,
    ShareResult,
)


class TestShareLinkModel:
    """Tests for ShareLink dataclass."""

    def test_share_link_creation(self):
        link = ShareLink(content_id="c1", token="abc123")
        assert link.content_id == "c1"
        assert link.token == "abc123"
        assert link.view_count == 0
        assert link.is_active is True

    def test_share_link_with_expiry(self):
        expiry = datetime.now(timezone.utc) + timedelta(days=7)
        link = ShareLink(content_id="c1", token="abc123", expires_at=expiry.isoformat())
        assert link.expires_at == expiry.isoformat()
        assert link.is_expired() is False

    def test_share_link_expired(self):
        expiry = datetime.now(timezone.utc) - timedelta(days=1)
        link = ShareLink(content_id="c1", token="abc123", expires_at=expiry.isoformat())
        assert link.is_expired() is True

    def test_share_link_no_expiry(self):
        link = ShareLink(content_id="c1", token="abc123")
        assert link.is_expired() is False

    def test_share_link_deactivate(self):
        link = ShareLink(content_id="c1", token="abc123")
        link.deactivate()
        assert link.is_active is False

    def test_share_link_increment_views(self):
        link = ShareLink(content_id="c1", token="abc123")
        link.increment_views()
        assert link.view_count == 1
        link.increment_views()
        assert link.view_count == 2

    def test_share_link_to_dict(self):
        link = ShareLink(content_id="c1", token="abc123")
        d = link.to_dict()
        assert d["content_id"] == "c1"
        assert d["token"] == "abc123"

    def test_share_link_from_dict(self):
        data = {
            "content_id": "c1",
            "token": "abc123",
            "view_count": 5,
            "is_active": True,
            "expires_at": None,
            "share_id": "share1",
            "created_at": "2024-01-01T00:00:00",
        }
        link = ShareLink.from_dict(data)
        assert link.content_id == "c1"
        assert link.token == "abc123"
        assert link.view_count == 5

    def test_share_link_repr(self):
        link = ShareLink(content_id="c1", token="abc123")
        assert "c1" in repr(link)


class TestShareFormat:
    """Tests for ShareFormat enum."""

    def test_share_format_values(self):
        assert ShareFormat.URL.value == "url"
        assert ShareFormat.QR_CODE.value == "qr_code"
        assert ShareFormat.MARKDOWN.value == "markdown"
        assert ShareFormat.HTML.value == "html"


class TestShareStore:
    """Tests for ShareStore class."""

    def setup_method(self):
        self.store = ShareStore(base_url="https://example.com/s")

    def test_create_share_link(self):
        result = self.store.create_share_link("c1")
        assert result is not None
        assert result.content_id == "c1"
        assert result.token != ""

    def test_create_share_link_with_expiry(self):
        expiry = datetime.now(timezone.utc) + timedelta(days=7)
        result = self.store.create_share_link("c1", expires_at=expiry)
        assert result.expires_at is not None

    def test_create_share_link_with_max_views(self):
        result = self.store.create_share_link("c1", max_views=10)
        assert result.max_views == 10

    def test_get_share_link_by_token(self):
        result = self.store.create_share_link("c1")
        link = self.store.get_by_token(result.token)
        assert link is not None
        assert link.content_id == "c1"

    def test_get_share_link_invalid_token(self):
        link = self.store.get_by_token("invalid")
        assert link is None

    def test_get_share_url(self):
        result = self.store.create_share_link("c1")
        url = self.store.get_share_url(result.token)
        assert "https://example.com/s/" in url
        assert result.token in url

    def test_list_share_links(self):
        self.store.create_share_link("c1")
        self.store.create_share_link("c2")
        links = self.store.list_share_links()
        assert len(links) == 2

    def test_list_share_links_for_content(self):
        self.store.create_share_link("c1")
        self.store.create_share_link("c2")
        self.store.create_share_link("c1")
        links = self.store.list_for_content("c1")
        assert len(links) == 2

    def test_deactivate_share_link(self):
        result = self.store.create_share_link("c1")
        self.store.deactivate(result.token)
        link = self.store.get_by_token(result.token)
        assert link.is_active is False

    def test_delete_share_link(self):
        result = self.store.create_share_link("c1")
        self.store.delete(result.token)
        assert self.store.get_by_token(result.token) is None

    def test_track_view(self):
        result = self.store.create_share_link("c1")
        self.store.track_view(result.token)
        link = self.store.get_by_token(result.token)
        assert link.view_count == 1

    def test_track_view_max_views_reached(self):
        result = self.store.create_share_link("c1", max_views=1)
        self.store.track_view(result.token)
        link = self.store.get_by_token(result.token)
        assert link.view_count == 1
        assert link.is_active is False

    def test_track_view_expired_link(self):
        expiry = datetime.now(timezone.utc) - timedelta(days=1)
        result = self.store.create_share_link("c1", expires_at=expiry)
        self.store.track_view(result.token)
        link = self.store.get_by_token(result.token)
        assert link.view_count == 0

    def test_generate_share_result_url(self):
        result = self.store.create_share_link("c1")
        share = self.store.generate_share(result.token, ShareFormat.URL)
        assert share.format == ShareFormat.URL
        assert result.token in share.content

    def test_generate_share_result_markdown(self):
        result = self.store.create_share_link("c1")
        share = self.store.generate_share(result.token, ShareFormat.MARKDOWN)
        assert share.format == ShareFormat.MARKDOWN
        assert "[" in share.content

    def test_generate_share_result_html(self):
        result = self.store.create_share_link("c1")
        share = self.store.generate_share(result.token, ShareFormat.HTML)
        assert share.format == ShareFormat.HTML
        assert "<a" in share.content

    def test_generate_share_result_qr_code(self):
        result = self.store.create_share_link("c1")
        share = self.store.generate_share(result.token, ShareFormat.QR_CODE)
        assert share.format == ShareFormat.QR_CODE

    def test_generate_share_invalid_token(self):
        share = self.store.generate_share("invalid", ShareFormat.URL)
        assert share is None

    def test_generate_share_inactive_link(self):
        result = self.store.create_share_link("c1")
        self.store.deactivate(result.token)
        share = self.store.generate_share(result.token, ShareFormat.URL)
        assert share is None

    def test_generate_share_expired_link(self):
        expiry = datetime.now(timezone.utc) - timedelta(days=1)
        result = self.store.create_share_link("c1", expires_at=expiry)
        share = self.store.generate_share(result.token, ShareFormat.URL)
        assert share is None

    def test_get_stats(self):
        self.store.create_share_link("c1")
        self.store.create_share_link("c2")
        stats = self.store.get_stats()
        assert stats["total_links"] == 2
        assert stats["active_links"] == 2

    def test_get_stats_with_views(self):
        result = self.store.create_share_link("c1")
        self.store.track_view(result.token)
        stats = self.store.get_stats()
        assert stats["total_views"] == 1

    def test_clear(self):
        self.store.create_share_link("c1")
        self.store.clear()
        assert self.store.list_share_links() == []

    def test_serialize_deserialize(self):
        self.store.create_share_link("c1")
        data = self.store.serialize()
        assert len(data) == 1
        new_store = ShareStore(base_url="https://example.com/s")
        new_store.deserialize(data)
        assert len(new_store.list_share_links()) == 1

    def test_custom_base_url(self):
        store = ShareStore(base_url="https://myapp.io/share")
        result = store.create_share_link("c1")
        url = store.get_share_url(result.token)
        assert "https://myapp.io/share/" in url

    def test_share_result_to_dict(self):
        result = self.store.create_share_link("c1")
        share = self.store.generate_share(result.token, ShareFormat.URL)
        d = share.to_dict()
        assert "format" in d
        assert "content" in d
        assert "share_id" in d
