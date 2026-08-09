"""Tests for GraphQL request/response."""

from __future__ import annotations

import pytest
from personal_index.content_api_graphql import GraphQLRequest, GraphQLResponse


class TestGraphQLRequest:
    def test_minimal_request(self):
        req = GraphQLRequest(query="{ test }")
        assert req.query == "{ test }"

    def test_request_with_all_fields(self):
        req = GraphQLRequest(
            query="query($id: ID!) { item(id: $id) }",
            variables={"id": "1"},
            operation_name="GetItem"
        )
        assert req.operation_name == "GetItem"

    def test_request_serialization(self):
        req = GraphQLRequest(query="{ test }", variables={"a": 1})
        d = req.to_dict()
        assert d["query"] == "{ test }"
        assert d["variables"] == {"a": 1}


class TestGraphQLResponse:
    def test_success_response(self):
        resp = GraphQLResponse(data={"result": "ok"})
        d = resp.to_dict()
        assert d["data"]["result"] == "ok"

    def test_error_response(self):
        resp = GraphQLResponse(
            data=None,
            errors=[{"message": "Error", "path": ["items"]}]
        )
        d = resp.to_dict()
        assert d["errors"][0]["path"] == ["items"]

    def test_empty_response(self):
        resp = GraphQLResponse()
        d = resp.to_dict()
        assert d == {}
