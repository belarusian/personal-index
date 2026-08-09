"""Tests for content_api_graphql module - GraphQL API for content queries."""

from __future__ import annotations

import pytest
from personal_index.content_api_graphql import (
    GraphQLSchema,
    ContentQuery,
    ContentMutation,
    ContentSubscription,
    GraphQLResponse,
    GraphQLRequest,
    create_graphql_schema,
    build_content_type,
    build_query_type,
    build_mutation_type,
)


class TestGraphQLResponse:
    def test_response_success(self):
        resp = GraphQLResponse(data={"items": []})
        assert resp.data == {"items": []}
        assert resp.errors is None

    def test_response_with_errors(self):
        resp = GraphQLResponse(data=None, errors=[{"message": "Bad query"}])
        assert resp.data is None
        assert len(resp.errors) == 1

    def test_response_to_dict(self):
        resp = GraphQLResponse(data={"key": "val"})
        d = resp.to_dict()
        assert d["data"] == {"key": "val"}

    def test_response_to_dict_with_errors(self):
        resp = GraphQLResponse(data=None, errors=[{"message": "err"}])
        d = resp.to_dict()
        assert d["errors"] == [{"message": "err"}]


class TestGraphQLRequest:
    def test_request_basic(self):
        req = GraphQLRequest(query="{ items { id } }")
        assert req.query == "{ items { id } }"
        assert req.variables is None
        assert req.operation_name is None

    def test_request_with_variables(self):
        req = GraphQLRequest(
            query="query($id: ID!) { item(id: $id) { title } }",
            variables={"id": "123"},
        )
        assert req.variables == {"id": "123"}

    def test_request_with_operation_name(self):
        req = GraphQLRequest(
            query="query GetItem { item { id } }",
            operation_name="GetItem",
        )
        assert req.operation_name == "GetItem"

    def test_request_to_dict(self):
        req = GraphQLRequest(query="{ test }", variables={"a": 1})
        d = req.to_dict()
        assert d["query"] == "{ test }"
        assert d["variables"] == {"a": 1}


class TestContentQuery:
    def test_query_init(self):
        q = ContentQuery()
        assert q is not None

    def test_query_list_items(self):
        q = ContentQuery()
        result = q.list_items()
        assert isinstance(result, dict)

    def test_query_get_item(self):
        q = ContentQuery()
        result = q.get_item("test-id")
        assert isinstance(result, dict)

    def test_query_search(self):
        q = ContentQuery()
        result = q.search("test query")
        assert isinstance(result, dict)

    def test_query_get_tags(self):
        q = ContentQuery()
        result = q.get_tags()
        assert isinstance(result, dict)

    def test_query_get_stats(self):
        q = ContentQuery()
        result = q.get_stats()
        assert isinstance(result, dict)


class TestContentMutation:
    def test_mutation_init(self):
        m = ContentMutation()
        assert m is not None

    def test_mutation_create_item(self):
        m = ContentMutation()
        result = m.create_item({"title": "New Item"})
        assert isinstance(result, dict)

    def test_mutation_update_item(self):
        m = ContentMutation()
        result = m.update_item("id-1", {"title": "Updated"})
        assert isinstance(result, dict)

    def test_mutation_delete_item(self):
        m = ContentMutation()
        result = m.delete_item("id-1")
        assert isinstance(result, dict)

    def test_mutation_add_tag(self):
        m = ContentMutation()
        result = m.add_tag("tech")
        assert isinstance(result, dict)

    def test_mutation_remove_tag(self):
        m = ContentMutation()
        result = m.remove_tag("tech")
        assert isinstance(result, dict)


class TestContentSubscription:
    def test_subscription_init(self):
        s = ContentSubscription()
        assert s is not None

    def test_subscription_types(self):
        s = ContentSubscription()
        assert hasattr(s, 'CONTENT_ADDED')
        assert hasattr(s, 'CONTENT_UPDATED')
        assert hasattr(s, 'CONTENT_DELETED')


class TestGraphQLSchema:
    def test_schema_init(self):
        schema = GraphQLSchema()
        assert schema is not None

    def test_schema_has_query(self):
        schema = GraphQLSchema()
        assert hasattr(schema, 'query')

    def test_schema_has_mutation(self):
        schema = GraphQLSchema()
        assert hasattr(schema, 'mutation')

    def test_schema_execute(self):
        schema = GraphQLSchema()
        result = schema.execute("{ __typename }")
        assert isinstance(result, dict)


class TestCreateGraphQLSchema:
    def test_create_returns_schema(self):
        schema = create_graphql_schema()
        assert schema is not None


class TestBuildContentType:
    def test_build_content_type(self):
        ct = build_content_type()
        assert ct is not None
        assert "id" in ct
        assert "title" in ct


class TestBuildQueryType:
    def test_build_query_type(self):
        qt = build_query_type()
        assert qt is not None
        assert "items" in qt


class TestBuildMutationType:
    def test_build_mutation_type(self):
        mt = build_mutation_type()
        assert mt is not None
        assert "createItem" in mt
