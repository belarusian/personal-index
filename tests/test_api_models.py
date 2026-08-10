"""Tests for personal_index.api.models."""

import pytest
from personal_index.api.models import (
    APIResponse,
    PaginatedResponse,
    SearchRequest,
    SearchResponse,
    ErrorResponse,
    APIError,
    NotFoundError,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
)


class TestAPIResponse:
    def test_to_dict_with_data(self):
        resp = APIResponse(success=True, data={"key": "value"}, message="OK")
        result = resp.to_dict()
        assert result == {"success": True, "data": {"key": "value"}, "message": "OK"}

    def test_to_dict_with_none_data(self):
        resp = APIResponse(success=True)
        result = resp.to_dict()
        assert result == {"success": True}

    def test_to_dict_with_error(self):
        resp = APIResponse(success=False, error="bad_request", message="Invalid input")
        result = resp.to_dict()
        assert result == {"success": False, "error": "bad_request", "message": "Invalid input"}

    def test_to_dict_with_meta(self):
        resp = APIResponse(success=True, meta={"page": 1})
        result = resp.to_dict()
        assert result == {"success": True, "meta": {"page": 1}}

    def test_to_dict_with_object_data(self):
        class HasToDict:
            def to_dict(self):
                return {"nested": True}
        resp = APIResponse(success=True, data=HasToDict())
        result = resp.to_dict()
        assert result == {"success": True, "data": {"nested": True}}

    def test_to_dict_type_annotation(self):
        """Verify to_dict returns Dict[str, Any] - TICKET-81 fix."""
        resp = APIResponse(success=True, data=42, error="err", message="msg", meta={"x": 1})
        result = resp.to_dict()
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["data"] == 42
        assert result["error"] == "err"
        assert result["message"] == "msg"
        assert result["meta"] == {"x": 1}

    def test_ok_classmethod(self):
        resp = APIResponse.ok(data="hello")
        assert resp.success is True
        assert resp.data == "hello"
        assert resp.message == "Success"

    def test_error_response_classmethod(self):
        resp = APIResponse.error_response(message="Something failed")
        assert resp.success is False
        assert resp.error == "error"
        assert resp.message == "Something failed"


class TestPaginatedResponse:
    def test_to_dict(self):
        resp = PaginatedResponse(items=[1, 2], total=10, page=1, page_size=5, has_next=True, has_prev=False)
        result = resp.to_dict()
        assert result["items"] == [1, 2]
        assert result["total"] == 10
        assert result["total_pages"] == 2

    def test_total_pages_zero_page_size(self):
        resp = PaginatedResponse(items=[], total=0, page=1, page_size=0, has_next=False, has_prev=False)
        assert resp.total_pages == 0


class TestSearchRequest:
    def test_validate_empty_query(self):
        req = SearchRequest(q="")
        errors = req.validate()
        assert "Query cannot be empty" in errors

    def test_validate_limit_out_of_range(self):
        req = SearchRequest(q="test", limit=200)
        errors = req.validate()
        assert "Limit must be between 1 and 100" in errors

    def test_validate_negative_offset(self):
        req = SearchRequest(q="test", offset=-1)
        errors = req.validate()
        assert "Offset must be non-negative" in errors

    def test_validate_invalid_sort_order(self):
        req = SearchRequest(q="test", sort_order="invalid")
        errors = req.validate()
        assert "Sort order must be 'asc' or 'desc'" in errors

    def test_validate_valid(self):
        req = SearchRequest(q="test", limit=10, offset=0, sort_order="asc")
        errors = req.validate()
        assert errors == []


class TestAPIError:
    def test_api_error(self):
        err = APIError("test error", status_code=500, error_code="internal")
        assert err.message == "test error"
        assert err.status_code == 500
        assert err.error_code == "internal"

    def test_not_found_error(self):
        err = NotFoundError()
        assert err.status_code == 404
        assert err.error_code == "not_found"

    def test_validation_error(self):
        err = ValidationError()
        assert err.status_code == 422
        assert err.error_code == "validation_error"

    def test_unauthorized_error(self):
        err = UnauthorizedError()
        assert err.status_code == 401
        assert err.error_code == "unauthorized"

    def test_forbidden_error(self):
        err = ForbiddenError()
        assert err.status_code == 403
        assert err.error_code == "forbidden"
