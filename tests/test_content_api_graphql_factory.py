"""Tests for GraphQL factory functions."""

from __future__ import annotations

import pytest
from personal_index.content_api_graphql import create_graphql_schema


class TestGraphQLFactory:
    def test_create_schema(self):
        schema = create_graphql_schema()
        assert schema is not None

    def test_schema_can_execute(self):
        schema = create_graphql_schema()
        result = schema.execute("{ __typename }")
        assert "data" in result

    def test_schema_has_components(self):
        schema = create_graphql_schema()
        assert hasattr(schema, 'query')
        assert hasattr(schema, 'mutation')
        assert hasattr(schema, 'subscription')
