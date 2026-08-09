"""Integration tests for GraphQL module."""

from __future__ import annotations

import pytest
from personal_index.content_api_graphql import (
    GraphQLSchema, GraphQLRequest, GraphQLResponse,
    ContentQuery, ContentMutation, ContentSubscription,
    create_graphql_schema,
)


class TestGraphQLIntegration:
    def test_full_schema(self):
        schema = GraphQLSchema()
        assert hasattr(schema, 'query')
        assert hasattr(schema, 'mutation')
        assert hasattr(schema, 'subscription')

    def test_query_and_mutation(self):
        schema = GraphQLSchema()
        q_result = schema.execute("{ __typename }")
        assert q_result["data"]["__typename"] == "RootQuery"

    def test_request_to_schema(self):
        req = GraphQLRequest(query="{ __typename }")
        schema = GraphQLSchema()
        result = schema.execute(req.query)
        assert "data" in result

    def test_subscription_types(self):
        s = ContentSubscription()
        assert s.CONTENT_ADDED == "content_added"
        assert s.CONTENT_UPDATED == "content_updated"
        assert s.CONTENT_DELETED == "content_deleted"

    def test_factory_and_execute(self):
        schema = create_graphql_schema()
        result = schema.execute("{ items { id } }")
        assert "data" in result
