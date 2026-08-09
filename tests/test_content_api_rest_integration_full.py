"""Full integration tests for REST module."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import (
    ContentResponse, ErrorResponse, PaginatedResponse,
    ContentListResponse, ContentRouter, create_router,
)


class TestRESTFullIntegration:
    def test_response_chain(self):
        data = PaginatedResponse(items=[1, 2], total=10, page=1, page_size=5)
        resp = ContentResponse(data=data.to_dict())
        d = resp.to_dict()
        assert d["data"]["total"] == 10

    def test_error_chain(self):
        err = ErrorResponse(message="Not found", code=404)
        resp = ContentResponse(success=False, error=err.message)
        d = resp.to_dict()
        assert d["error"] == "Not found"

    def test_router_and_response(self):
        router = ContentRouter()
        resp = ContentResponse(data={"status": "ok"})
        assert resp.data["status"] == "ok"

    def test_list_and_paginated(self):
        list_resp = ContentListResponse(items=[1, 2], total=2)
        page_resp = PaginatedResponse(items=[1, 2], total=2, page=1, page_size=10)
        assert list_resp.to_dict()["total"] == page_resp.to_dict()["total"]

    def test_create_router_and_use(self):
        app = create_router()
        assert app is not None
