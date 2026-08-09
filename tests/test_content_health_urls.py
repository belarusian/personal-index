"""Tests for content_health URL accessibility checking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pytest

from personal_index.content_health import (
    UrlHealthResult,
    check_url_accessibility,
    check_content_urls,
)


class TestUrlHealthResult:
    """Tests for the UrlHealthResult dataclass."""

    def test_accessible_url(self):
        """Result for an accessible URL."""
        result = UrlHealthResult(
            url="https://example.com/page",
            status_code=200,
            is_accessible=True,
            error=None,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
        assert result.is_accessible is True
        assert result.status_code == 200
        assert result.error is None

    def test_inaccessible_url(self):
        """Result for an inaccessible URL."""
        result = UrlHealthResult(
            url="https://example.com/missing",
            status_code=404,
            is_accessible=False,
            error="Not Found",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
        assert result.is_accessible is False
        assert result.status_code == 404
        assert result.error == "Not Found"

    def test_error_url(self):
        """Result for a URL that raised an exception."""
        result = UrlHealthResult(
            url="https://example.com/bad",
            status_code=None,
            is_accessible=False,
            error="Connection refused",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
        assert result.is_accessible is False
        assert result.status_code is None
        assert result.error == "Connection refused"

    def test_to_dict(self):
        """Result can be serialized to dict."""
        result = UrlHealthResult(
            url="https://example.com/page",
            status_code=200,
            is_accessible=True,
            error=None,
            checked_at="2024-01-01T00:00:00+00:00",
        )
        d = result.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["status_code"] == 200
        assert d["is_accessible"] is True
        assert d["error"] is None


class TestCheckUrlAccessibility:
    """Tests for check_url_accessibility."""

    def test_accessible_url_returns_true(self):
        """A URL returning 200 is marked accessible."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            result = check_url_accessibility("https://example.com/page")

        assert result.is_accessible is True
        assert result.status_code == 200
        assert result.error is None
        mock_head.assert_called_once_with(
            "https://example.com/page", timeout=5, allow_redirects=True
        )

    def test_3xx_redirect_returns_true(self):
        """A URL returning 301 is marked accessible (redirect)."""
        mock_response = MagicMock()
        mock_response.status_code = 301

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            result = check_url_accessibility("https://example.com/old")

        assert result.is_accessible is True
        assert result.status_code == 301

    def test_404_returns_false(self):
        """A URL returning 404 is marked inaccessible."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            result = check_url_accessibility("https://example.com/missing")

        assert result.is_accessible is False
        assert result.status_code == 404
        assert "404" in result.error

    def test_500_returns_false(self):
        """A URL returning 500 is marked inaccessible."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            result = check_url_accessibility("https://example.com/error")

        assert result.is_accessible is False
        assert result.status_code == 500
        assert "500" in result.error

    def test_connection_error_returns_false(self):
        """A URL that raises a connection error is marked inaccessible."""
        import requests as req

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.side_effect = req.ConnectionError("Connection refused")
            result = check_url_accessibility("https://example.com/bad")

        assert result.is_accessible is False
        assert result.status_code is None
        assert "Connection refused" in result.error

    def test_timeout_returns_false(self):
        """A URL that times out is marked inaccessible."""
        import requests as req

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.side_effect = req.Timeout("Request timed out")
            result = check_url_accessibility("https://example.com/slow")

        assert result.is_accessible is False
        assert result.status_code is None
        assert "timed out" in result.error

    def test_custom_timeout(self):
        """Custom timeout is passed through."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            check_url_accessibility("https://example.com/page", timeout=10)

        mock_head.assert_called_once_with(
            "https://example.com/page", timeout=10, allow_redirects=True
        )

    def test_head_fallback_to_get(self):
        """If HEAD is not allowed (405), falls back to GET."""
        mock_head_response = MagicMock()
        mock_head_response.status_code = 405
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200

        with patch("personal_index.content_health.requests.head") as mock_head, \
             patch("personal_index.content_health.requests.get") as mock_get:
            mock_head.return_value = mock_head_response
            mock_get.return_value = mock_get_response
            result = check_url_accessibility("https://example.com/nohead")

        assert result.is_accessible is True
        mock_get.assert_called_once()

    def test_checked_at_is_set(self):
        """checked_at contains a valid ISO timestamp."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            result = check_url_accessibility("https://example.com/page")

        assert "T" in result.checked_at

    def test_empty_url_returns_inaccessible(self):
        """An empty URL is marked inaccessible."""
        result = check_url_accessibility("")
        assert result.is_accessible is False
        assert result.error is not None


class TestCheckContentUrls:
    """Tests for check_content_urls."""

    def _make_mock_storage(self, pages):
        """Create a mock storage with given pages."""
        mock_storage = MagicMock()
        mock_storage.get_pages.return_value = pages
        return mock_storage

    def test_empty_storage_returns_empty_results(self):
        """No pages means no results."""
        mock_storage = self._make_mock_storage([])
        results = check_content_urls(mock_storage)
        assert results == []

    def test_all_accessible(self):
        """All accessible URLs return True."""
        from personal_index.models import IndexedPage

        pages = [
            IndexedPage(url="https://example.com/page1", title="Page 1"),
            IndexedPage(url="https://example.com/page2", title="Page 2"),
        ]
        mock_storage = self._make_mock_storage(pages)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            results = check_content_urls(mock_storage)

        assert len(results) == 2
        assert all(r.is_accessible for r in results)

    def test_mixed_results(self):
        """Some accessible, some not."""
        from personal_index.models import IndexedPage

        pages = [
            IndexedPage(url="https://example.com/good", title="Good"),
            IndexedPage(url="https://example.com/bad", title="Bad"),
        ]
        mock_storage = self._make_mock_storage(pages)

        def side_effect(url, **kwargs):
            resp = MagicMock()
            if "good" in url:
                resp.status_code = 200
            else:
                resp.status_code = 404
            return resp

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.side_effect = side_effect
            results = check_content_urls(mock_storage)

        assert len(results) == 2
        assert results[0].is_accessible is True
        assert results[1].is_accessible is False

    def test_custom_timeout_propagated(self):
        """Custom timeout is passed to each check."""
        from personal_index.models import IndexedPage

        pages = [
            IndexedPage(url="https://example.com/page", title="Page"),
        ]
        mock_storage = self._make_mock_storage(pages)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            check_content_urls(mock_storage, timeout=15)

        mock_head.assert_called_once_with(
            "https://example.com/page", timeout=15, allow_redirects=True
        )

    def test_skips_invalid_urls(self):
        """Invalid URLs are skipped gracefully."""
        from personal_index.models import IndexedPage

        pages = [
            IndexedPage(url="not-a-url", title="Bad URL"),
            IndexedPage(url="https://example.com/good", title="Good"),
        ]
        mock_storage = self._make_mock_storage(pages)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("personal_index.content_health.requests.head") as mock_head:
            mock_head.return_value = mock_response
            results = check_content_urls(mock_storage)

        # Should have results for both - invalid URL gets error, valid one gets 200
        assert len(results) == 2
        assert results[0].is_accessible is False
        assert results[1].is_accessible is True
