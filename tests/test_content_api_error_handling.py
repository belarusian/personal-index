"""Tests for API error handling."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import ErrorResponse, ContentResponse
from personal_index.content_api_graphql import GraphQLResponse


class TestRESTErrorHandling:
    def test_not_found_error(self):
        err = ErrorResponse(message="Not found", code=404)
        d = err.to_dict()
        assert d["code"] == 404

    def test_unauthorized_error(self):
        err = ErrorResponse(message="Unauthorized", code=401)
        d = err.to_dict()
        assert d["code"] == 401

    def test_forbidden_error(self):
        err = ErrorResponse(message="Forbidden", code=403)
        d = err.to_dict()
        assert d["code"] == 403

    def test_bad_request_with_details(self):
        err = ErrorResponse(
            message="Bad request", code=400,
            details=["invalid field: name"]
        )
        d = err.to_dict()
        assert "invalid field" in d["details"][0]

    def test_content_response_error(self):
        resp = ContentResponse(success=False, error="Something went wrong")
        d = resp.to_dict()
        assert d["success"] is False
        assert d["error"] == "Something went wrong"


class TestGraphQLErrorHandling:
    def test_graphql_error_response(self):
        resp = GraphQLResponse(data=None, errors=[{"message": "Field not found"}])
        d = resp.to_dict()
        assert d["errors"][0]["message"] == "Field not found"

    def test_graphql_partial_error(self):
        resp = GraphQLResponse(
            data={"items": []},
            errors=[{"message": "Warning"}]
        )
        d = resp.to_dict()
        assert d["data"]["items"] == []
        assert d["errors"][0]["message"] == "Warning"
