"""Tests for GraphQL schema building."""

from __future__ import annotations

import pytest
from personal_index.content_api_graphql import (
    GraphQLSchema,
    build_content_type,
    build_query_type,
    build_mutation_type,
)


class TestSchemaTypes:
    def test_content_type_fields(self):
        ct = build_content_type()
        assert "id" in ct
        assert "title" in ct
        assert "url" in ct
        assert "content" in ct
        assert "tags" in ct
        assert "created_at" in ct
        assert "updated_at" in ct

    def test_query_type_fields(self):
        qt = build_query_type()
        assert "items" in qt
        assert "item" in qt
        assert "search" in qt
        assert "tags" in qt
        assert "stats" in qt

    def test_mutation_type_fields(self):
        mt = build_mutation_type()
        assert "createItem" in mt
        assert "updateItem" in mt
        assert "deleteItem" in mt
        assert "addTag" in mt
        assert "removeTag" in mt


class TestSchemaExecution:
    def test_execute_items_query(self):
        schema = GraphQLSchema()
        result = schema.execute("{ items { id } }")
        assert "data" in result

    def test_execute_search_query(self):
        schema = GraphQLSchema()
        result = schema.execute('query { search(query: "test") { results } }')
        assert "data" in result

    def test_execute_typename_query(self):
        schema = GraphQLSchema()
        result = schema.execute("{ __typename }")
        assert result["data"]["__typename"] == "RootQuery"

    def test_execute_with_variables(self):
        schema = GraphQLSchema()
        result = schema.execute(
            "query($q: String) { search(query: $q) { results } }",
            variables={"q": "test"}
        )
        assert "data" in result
