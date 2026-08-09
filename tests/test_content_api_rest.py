"""Tests for content_api_rest module - REST API for content operations."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from personal_index.content_api_rest import (
    create_router,
    ContentRouter,
    ContentResponse,
    ErrorResponse,
    PaginatedResponse,
    ContentListResponse,
)


class TestContentResponse:
    def test_content_response_success(self):
        resp = ContentResponse(data={"title": "Test", "url": "http://test.com"})
        assert resp.success is True
        assert resp.data == {"title": "Test", "url": "http://test.com"}
        assert resp.error is None

    def test_content_response_error(self):
        resp = ContentResponse(success=False, error="Not found")
        assert resp.success is False
        assert resp.error == "Not found"
        assert resp.data is None

    def test_content_response_to_dict(self):
        resp = ContentResponse(data={"key": "value"})
        d = resp.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "value"}


class TestErrorResponse:
    def test_error_response_basic(self):
        err = ErrorResponse(message="Bad request", code=400)
        assert err.message == "Bad request"
        assert err.code == 400

    def test_error_response_with_details(self):
        err = ErrorResponse(message="Validation error", code=422, details=["field required"])
        assert err.details == ["field required"]

    def test_error_response_to_dict(self):
        err = ErrorResponse(message="Not found", code=404)
        d = err.to_dict()
        assert d["error"] == "Not found"
        assert d["code"] == 404


class TestPaginatedResponse:
    def test_paginated_response(self):
        resp = PaginatedResponse(items=[1, 2, 3], total=10, page=1, page_size=10)
        assert resp.items == [1, 2, 3]
        assert resp.total == 10
        assert resp.page == 1
        assert resp.page_size == 10
        assert resp.total_pages == 1

    def test_paginated_response_multiple_pages(self):
        resp = PaginatedResponse(items=[1], total=25, page=1, page_size=10)
        assert resp.total_pages == 3

    def test_paginated_response_to_dict(self):
        resp = PaginatedResponse(items=[1], total=5, page=1, page_size=2)
        d = resp.to_dict()
        assert d["items"] == [1]
        assert d["total"] == 5
        assert d["page"] == 1
        assert d["page_size"] == 2
        assert d["total_pages"] == 3


class TestContentListResponse:
    def test_content_list_response(self):
        resp = ContentListResponse(items=[], total=0)
        assert resp.items == []
        assert resp.total == 0

    def test_content_list_response_with_items(self):
        items = [{"url": "http://a.com"}, {"url": "http://b.com"}]
        resp = ContentListResponse(items=items, total=2)
        assert len(resp.items) == 2
        assert resp.total == 2


class TestCreateRouter:
    def test_create_router_returns_router(self):
        router = create_router()
        assert router is not None

    def test_create_router_with_custom_prefix(self):
        router = create_router(prefix="/api/v2")
        assert router is not None


class TestContentRouter:
    def test_router_init(self):
        router = ContentRouter()
        assert router is not None

    def test_router_has_routes(self):
        router = ContentRouter()
        assert hasattr(router, 'app')

    def test_router_health_check(self):
        router = ContentRouter()
        assert hasattr(router, 'app')
