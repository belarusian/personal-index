"""Tests for REST router configuration."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import ContentRouter, create_router


class TestContentRouter:
    def test_default_prefix(self):
        router = ContentRouter()
        assert router is not None

    def test_custom_prefix(self):
        router = ContentRouter(prefix="/api/v2/content")
        assert router is not None

    def test_router_has_app(self):
        router = ContentRouter()
        assert hasattr(router, 'app')

    def test_router_has_routes_attr(self):
        router = ContentRouter()
        assert hasattr(router, 'router')


class TestCreateRouter:
    def test_default_create(self):
        app = create_router()
        assert app is not None

    def test_custom_prefix_create(self):
        app = create_router(prefix="/api/v2")
        assert app is not None
