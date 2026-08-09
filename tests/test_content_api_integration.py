"""Integration tests combining multiple API modules."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import ContentResponse, PaginatedResponse
from personal_index.content_api_auth import APIAuth, AuthMiddleware
from personal_index.content_api_rate_limit import RateLimiter, RateLimitMiddleware
from personal_index.content_api_docs import APIDocumentation, EndpointDoc
from personal_index.content_api_graphql import GraphQLSchema


class TestAPIIntegration:
    def test_auth_with_rate_limit(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        result = limiter.check("user1")
        assert result.allowed is True
        payload = auth.validate_token(token)
        assert payload is not None

    def test_rest_response_with_pagination(self):
        resp = ContentResponse(
            data=PaginatedResponse(
                items=[{"id": 1}], total=1, page=1, page_size=10
            ).to_dict()
        )
        assert resp.data["total"] == 1

    def test_graphql_with_auth(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        schema = GraphQLSchema()
        result = schema.execute("{ __typename }")
        assert "data" in result
        payload = auth.validate_token(token)
        assert payload is not None

    def test_docs_with_endpoints(self):
        docs = APIDocumentation()
        docs.add_endpoint(
            EndpointDoc(path="/items", method="GET", summary="List items")
        )
        generated = docs.generate()
        assert len(generated["endpoints"]) == 1
