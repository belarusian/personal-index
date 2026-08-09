"""Complete GraphQL module tests."""

from __future__ import annotations

import pytest
from personal_index.content_api_graphql import (
    GraphQLSchema, GraphQLRequest, GraphQLResponse,
    ContentQuery, ContentMutation, ContentSubscription,
    create_graphql_schema, build_content_type,
    build_query_type, build_mutation_type,
)


class TestGraphQLComplete:
    def test_all_exports(self):
        assert GraphQLSchema is not None
        assert GraphQLRequest is not None
        assert GraphQLResponse is not None
        assert ContentQuery is not None
        assert ContentMutation is not None
        assert ContentSubscription is not None

    def test_all_builders(self):
        ct = build_content_type()
        qt = build_query_type()
        mt = build_mutation_type()
        assert "id" in ct
        assert "items" in qt
        assert "createItem" in mt

    def test_factory(self):
        schema = create_graphql_schema()
        assert schema is not None

    def test_full_workflow(self):
        schema = create_graphql_schema()
        req = GraphQLRequest(query="{ __typename }")
        result = schema.execute(req.query)
        assert result["data"]["__typename"] == "RootQuery"
