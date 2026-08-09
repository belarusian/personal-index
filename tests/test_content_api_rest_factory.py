"""Tests for REST factory functions."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import create_router, ContentRouter


class TestRESTFactory:
    def test_create_router_default(self):
        app = create_router()
        assert app is not None

    def test_create_router_custom_prefix(self):
        app = create_router(prefix="/api/v2/content")
        assert app is not None

    def test_router_instance(self):
        router = ContentRouter()
        assert router is not None
        assert hasattr(router, 'app')
