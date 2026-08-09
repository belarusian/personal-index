"""Tests for GraphQL subscriptions."""

from __future__ import annotations

import pytest
from personal_index.content_api_graphql import ContentSubscription


class TestContentSubscription:
    def test_content_added_type(self):
        s = ContentSubscription()
        assert s.CONTENT_ADDED == "content_added"

    def test_content_updated_type(self):
        s = ContentSubscription()
        assert s.CONTENT_UPDATED == "content_updated"

    def test_content_deleted_type(self):
        s = ContentSubscription()
        assert s.CONTENT_DELETED == "content_deleted"

    def test_on_content_added(self):
        s = ContentSubscription()
        result = s.on_content_added()
        assert result["type"] == "content_added"

    def test_on_content_updated(self):
        s = ContentSubscription()
        result = s.on_content_updated()
        assert result["type"] == "content_updated"

    def test_on_content_deleted(self):
        s = ContentSubscription()
        result = s.on_content_deleted()
        assert result["type"] == "content_deleted"
