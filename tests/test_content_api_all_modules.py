"""Tests verifying all API modules work together."""

from __future__ import annotations

import pytest


class TestAllModules:
    def test_import_rest(self):
        from personal_index.content_api_rest import ContentResponse
        assert ContentResponse is not None

    def test_import_graphql(self):
        from personal_index.content_api_graphql import GraphQLSchema
        assert GraphQLSchema is not None

    def test_import_docs(self):
        from personal_index.content_api_docs import APIDocumentation
        assert APIDocumentation is not None

    def test_import_auth(self):
        from personal_index.content_api_auth import APIAuth
        assert APIAuth is not None

    def test_import_rate_limit(self):
        from personal_index.content_api_rate_limit import RateLimiter
        assert RateLimiter is not None

    def test_cross_module_rest_auth(self):
        from personal_index.content_api_rest import ContentResponse
        from personal_index.content_api_auth import APIAuth
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        resp = ContentResponse(data={"token_valid": token is not None})
        assert resp.data["token_valid"] is True

    def test_cross_module_graphql_docs(self):
        from personal_index.content_api_graphql import GraphQLSchema
        from personal_index.content_api_docs import EndpointDoc, generate_openapi_spec
        schema = GraphQLSchema()
        spec = generate_openapi_spec([
            EndpointDoc(path="/graphql", method="POST", summary="GraphQL endpoint")
        ])
        assert "/graphql" in spec["paths"]

    def test_cross_module_auth_rate_limit(self):
        from personal_index.content_api_auth import APIAuth
        from personal_index.content_api_rate_limit import RateLimiter
        auth = APIAuth()
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        token = auth.generate_token("user1", ["read"])
        result = limiter.check("user1")
        assert token is not None
        assert result.allowed is True
