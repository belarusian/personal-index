"""Tests for GraphQL resolvers."""

from __future__ import annotations

import pytest
from personal_index.content_api_graphql import ContentQuery, ContentMutation


class TestQueryResolvers:
    def test_list_items_pagination(self):
        q = ContentQuery()
        result = q.list_items(page=2, page_size=10)
        assert result["page"] == 2
        assert result["page_size"] == 10

    def test_get_item_returns_dict(self):
        q = ContentQuery()
        result = q.get_item("abc-123")
        assert result["id"] == "abc-123"

    def test_search_returns_results(self):
        q = ContentQuery()
        result = q.search("python")
        assert result["query"] == "python"
        assert "results" in result

    def test_get_tags_returns_list(self):
        q = ContentQuery()
        result = q.get_tags()
        assert "tags" in result
        assert isinstance(result["tags"], list)

    def test_get_stats_returns_dict(self):
        q = ContentQuery()
        result = q.get_stats()
        assert "total_items" in result
        assert "total_tags" in result


class TestMutationResolvers:
    def test_create_item_returns_success(self):
        m = ContentMutation()
        result = m.create_item({"title": "New"})
        assert result["success"] is True
        assert "item" in result

    def test_update_item_preserves_id(self):
        m = ContentMutation()
        result = m.update_item("id-1", {"title": "Updated"})
        assert result["item"]["id"] == "id-1"

    def test_delete_item_returns_id(self):
        m = ContentMutation()
        result = m.delete_item("id-1")
        assert result["deleted_id"] == "id-1"

    def test_add_tag_returns_tag(self):
        m = ContentMutation()
        result = m.add_tag("python")
        assert result["tag"]["name"] == "python"

    def test_remove_tag_returns_name(self):
        m = ContentMutation()
        result = m.remove_tag("python")
        assert result["removed_tag"] == "python"
