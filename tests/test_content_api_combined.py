"""Combined API tests for all modules."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import ContentResponse, ErrorResponse, PaginatedResponse
from personal_index.content_api_graphql import GraphQLSchema, GraphQLResponse
from personal_index.content_api_docs import APIDocumentation, EndpointDoc, generate_openapi_spec
from personal_index.content_api_auth import APIAuth, AuthMiddleware, TokenManager
from personal_index.content_api_rate_limit import RateLimiter, RateLimitMiddleware, SlidingWindowLimiter


class TestCombinedAPI:
    def test_full_auth_flow(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read", "write"])
        payload = auth.validate_token(token)
        assert payload.user_id == "user1"
        assert auth.check_permission("user1", payload.permissions, "read")

    def test_full_rate_limit_flow(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for i in range(3):
            result = limiter.check("user1")
            assert result.allowed is True
        result = limiter.check("user1")
        assert result.allowed is False

    def test_full_docs_flow(self):
        docs = APIDocumentation()
        docs.add_endpoint(EndpointDoc(path="/items", method="GET", summary="List"))
        spec = generate_openapi_spec(docs.endpoints)
        assert "/items" in spec["paths"]

    def test_full_graphql_flow(self):
        schema = GraphQLSchema()
        result = schema.execute("{ __typename }")
        assert result["data"]["__typename"] == "RootQuery"

    def test_middleware_chain(self):
        auth_mw = AuthMiddleware()
        rate_mw = RateLimitMiddleware(max_requests=100, window_seconds=60)
        token = auth_mw.auth.generate_token("user1", ["read"])
        auth_result = auth_mw.process_request(
            {"headers": {"Authorization": f"Bearer {token}"}}
        )
        rate_result = rate_mw.process_request({"client_ip": "127.0.0.1"})
        assert auth_result["authenticated"] is True
        assert rate_result["allowed"] is True
