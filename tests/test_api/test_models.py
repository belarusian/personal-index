"""Tests for API request/response models."""

from __future__ import annotations

import pytest

from personal_index.api.models import (
    APIError,
    APIResponse,
    ErrorResponse,
    ForbiddenError,
    NotFoundError,
    PaginatedResponse,
    SearchRequest,
    SearchResponse,
    UnauthorizedError,
    ValidationError,
)


class TestAPIResponse:
    def test_ok_response(self):
        resp = APIResponse.ok(data={"key": "value"})
        assert resp.success is True
        assert resp.data == {"key": "value"}

    def test_error_response(self):
        resp = APIResponse.error_response(message="Something failed", error_code="fail")
        assert resp.success is False
        assert resp.error == "fail"
        assert resp.message == "Something failed"

    def test_to_dict_with_data(self):
        resp = APIResponse.ok(data={"name": "test"})
        data = resp.to_dict()
        assert data["success"] is True
        assert data["data"] == {"name": "test"}

    def test_to_dict_with_error(self):
        resp = APIResponse.error_response(message="Not found", error_code="not_found")
        data = resp.to_dict()
        assert data["success"] is False
        assert data["error"] == "not_found"

    def test_to_dict_with_object(self):
        from personal_index.models import IndexedPage
        page = IndexedPage(url="http://example.com", title="Test")
        resp = APIResponse.ok(data=page)
        data = resp.to_dict()
        assert data["data"]["url"] == "http://example.com"

    def test_to_dict_with_meta(self):
        resp = APIResponse(success=True, data="ok", meta={"version": "1.0"})
        data = resp.to_dict()
        assert data["meta"]["version"] == "1.0"

    def test_ok_response_message(self):
        resp = APIResponse.ok(data="result", message="All good")
        assert resp.message == "All good"

    def test_error_without_code(self):
        resp = APIResponse.error_response(message="Generic error")
        assert resp.error == "error"


class TestPaginatedResponse:
    def test_paginated_response(self):
        resp = PaginatedResponse(
            items=[1, 2, 3], total=30, page=1, page_size=10,
            has_next=True, has_prev=False,
        )
        assert resp.total_pages == 3
        assert resp.has_next is True

    def test_to_dict(self):
        resp = PaginatedResponse(
            items=[{"id": 1}], total=5, page=1, page_size=3,
            has_next=True, has_prev=False,
        )
        data = resp.to_dict()
        assert data["total"] == 5
        assert data["total_pages"] == 2
        assert data["has_next"] is True

    def test_total_pages_zero_items(self):
        resp = PaginatedResponse(
            items=[], total=0, page=1, page_size=10,
            has_next=False, has_prev=False,
        )
        assert resp.total_pages == 0


class TestSearchRequest:
    def test_valid_request(self):
        req = SearchRequest(q="python")
        assert req.validate() == []

    def test_empty_query(self):
        req = SearchRequest(q="")
        errors = req.validate()
        assert any("empty" in e.lower() for e in errors)

    def test_whitespace_query(self):
        req = SearchRequest(q="   ")
        errors = req.validate()
        assert any("empty" in e.lower() for e in errors)

    def test_limit_too_small(self):
        req = SearchRequest(q="test", limit=0)
        errors = req.validate()
        assert any("limit" in e.lower() for e in errors)

    def test_limit_too_large(self):
        req = SearchRequest(q="test", limit=200)
        errors = req.validate()
        assert any("limit" in e.lower() for e in errors)

    def test_negative_offset(self):
        req = SearchRequest(q="test", offset=-1)
        errors = req.validate()
        assert any("offset" in e.lower() for e in errors)

    def test_invalid_sort_order(self):
        req = SearchRequest(q="test", sort_order="invalid")
        errors = req.validate()
        assert any("sort" in e.lower() for e in errors)


class TestSearchResponse:
    def test_search_response(self):
        resp = SearchResponse(
            query="python", results=[{"url": "http://x.com"}],
            total=1, limit=20, offset=0, execution_time_ms=5.2,
        )
        data = resp.to_dict()
        assert data["query"] == "python"
        assert data["execution_time_ms"] == 5.2


class TestErrorResponse:
    def test_error_response(self):
        resp = ErrorResponse(error="not_found", message="Page not found", status_code=404)
        data = resp.to_dict()
        assert data["status_code"] == 404
        assert "details" not in data

    def test_error_response_with_details(self):
        resp = ErrorResponse(
            error="validation", message="Bad input",
            details={"field": "email"},
        )
        data = resp.to_dict()
        assert data["details"]["field"] == "email"


class TestAPIErrors:
    def test_api_error(self):
        exc = APIError("Something wrong", status_code=400, error_code="bad")
        assert exc.message == "Something wrong"
        assert exc.status_code == 400

    def test_not_found_error(self):
        exc = NotFoundError("User not found")
        assert exc.status_code == 404
        assert exc.error_code == "not_found"

    def test_validation_error(self):
        exc = ValidationError("Invalid email", details={"field": "email"})
        assert exc.status_code == 422
        assert exc.error_code == "validation_error"

    def test_unauthorized_error(self):
        exc = UnauthorizedError()
        assert exc.status_code == 401

    def test_forbidden_error(self):
        exc = ForbiddenError("No access")
        assert exc.status_code == 403

class TestAPIResponseNoNamingConflict:
    """TICKET-19: Verify error field and error_response classmethod coexist."""

    def test_error_field_and_error_response_method_coexist(self):
        """The error field and error_response classmethod should not conflict."""
        # error_response classmethod should work
        resp = APIResponse.error_response(message="fail", error_code="code123")
        assert resp.success is False
        assert resp.error == "code123"
        assert resp.message == "fail"

    def test_error_field_is_accessible_on_instance(self):
        """The error dataclass field should be directly accessible."""
        resp = APIResponse(success=False, error="my_error", message="oops")
        assert resp.error == "my_error"

    def test_error_field_can_be_set_independently(self):
        """The error field should be settable without calling error_response."""
        resp = APIResponse(success=True, data="ok", error="partial_error")
        assert resp.success is True
        assert resp.error == "partial_error"

    def test_error_response_returns_correct_type(self):
        """error_response should return an APIResponse instance."""
        resp = APIResponse.error_response(message="test")
        assert isinstance(resp, APIResponse)
        assert resp.success is False
