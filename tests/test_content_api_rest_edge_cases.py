"""Edge case tests for REST module."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import (
    ContentResponse, ErrorResponse, PaginatedResponse,
    ContentListResponse, ContentRouter,
)


class TestRESTEdgeCases:
    def test_response_large_data(self):
        data = {"items": [{"id": i} for i in range(1000)]}
        resp = ContentResponse(data=data)
        assert len(resp.data["items"]) == 1000

    def test_error_unicode_message(self):
        err = ErrorResponse(message="Ошибка", code=500)
        d = err.to_dict()
        assert d["error"] == "Ошибка"

    def test_paginated_huge_total(self):
        resp = PaginatedResponse(items=[], total=1000000, page=1, page_size=10)
        assert resp.total_pages == 100000

    def test_list_response_empty(self):
        resp = ContentListResponse(items=[], total=0)
        d = resp.to_dict()
        assert d["items"] == []
        assert d["total"] == 0

    def test_router_no_fastapi(self):
        router = ContentRouter()
        assert router is not None
