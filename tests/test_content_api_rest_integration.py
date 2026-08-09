"""Integration tests for content_api_rest module."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import (
    ContentResponse,
    ErrorResponse,
    PaginatedResponse,
    ContentListResponse,
    ContentRouter,
)


class TestContentResponseEdgeCases:
    def test_response_none_data(self):
        resp = ContentResponse(success=True, data=None)
        assert resp.data is None

    def test_response_empty_dict(self):
        resp = ContentResponse(data={})
        assert resp.data == {}

    def test_response_nested_data(self):
        resp = ContentResponse(data={"nested": {"key": "value"}})
        assert resp.data["nested"]["key"] == "value"

    def test_response_error_with_data(self):
        resp = ContentResponse(success=False, data={}, error="Partial error")
        assert resp.success is False
        assert resp.error == "Partial error"


class TestErrorResponseEdgeCases:
    def test_error_500(self):
        err = ErrorResponse(message="Internal error", code=500)
        assert err.code == 500

    def test_error_401(self):
        err = ErrorResponse(message="Unauthorized", code=401)
        assert err.code == 401

    def test_error_empty_details(self):
        err = ErrorResponse(message="Error", code=400, details=[])
        assert err.details == []

    def test_error_multiple_details(self):
        err = ErrorResponse(
            message="Validation", code=422,
            details=["field1 required", "field2 invalid"]
        )
        assert len(err.details) == 2


class TestPaginatedResponseEdgeCases:
    def test_paginated_zero_total(self):
        resp = PaginatedResponse(items=[], total=0, page=1, page_size=10)
        assert resp.total_pages == 1

    def test_paginated_exact_pages(self):
        resp = PaginatedResponse(items=[], total=20, page=1, page_size=10)
        assert resp.total_pages == 2

    def test_paginated_large_page_size(self):
        resp = PaginatedResponse(items=[], total=5, page=1, page_size=100)
        assert resp.total_pages == 1

    def test_paginated_page_size_one(self):
        resp = PaginatedResponse(items=[], total=10, page=1, page_size=1)
        assert resp.total_pages == 10
