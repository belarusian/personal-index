"""Complete REST module tests."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import (
    ContentResponse, ErrorResponse, PaginatedResponse,
    ContentListResponse, ContentRouter, create_router,
)


class TestRESTComplete:
    def test_all_exports(self):
        assert ContentResponse is not None
        assert ErrorResponse is not None
        assert PaginatedResponse is not None
        assert ContentListResponse is not None
        assert ContentRouter is not None

    def test_all_types(self):
        resp = ContentResponse(data={"key": "val"})
        err = ErrorResponse(message="Error", code=400)
        page = PaginatedResponse(items=[], total=0, page=1, page_size=10)
        lst = ContentListResponse(items=[], total=0)
        assert resp.to_dict()["success"] is True
        assert err.to_dict()["code"] == 400
        assert page.to_dict()["total_pages"] == 1
        assert lst.to_dict()["total"] == 0

    def test_factory(self):
        app = create_router()
        assert app is not None

    def test_full_workflow(self):
        router = ContentRouter()
        resp = ContentResponse(
            data=PaginatedResponse(
                items=[{"id": 1}], total=1, page=1, page_size=10
            ).to_dict()
        )
        d = resp.to_dict()
        assert d["data"]["total"] == 1
