"""Tests for personal_index.api.server — FastAPI server entry point."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from personal_index.api.server import create_app, lifespan


class TestCreateApp:
    """Tests for create_app factory function."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        from fastapi import FastAPI
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_create_app_has_correct_title(self):
        """Test that app has the correct title."""
        app = create_app()
        assert app.title == "Personal Index API"

    def test_create_app_has_description(self):
        """Test that app has a description."""
        app = create_app()
        assert app.description == "REST API for the personal web search engine"

    def test_create_app_has_version(self):
        """Test that app has version set."""
        app = create_app()
        assert app.version == "0.1.0"

    def test_create_app_with_config(self):
        """Test creating app with custom AppConfig."""
        from personal_index.config.models import AppConfig
        config = AppConfig()
        app = create_app(config=config)
        assert app.state.config is config

    def test_create_app_with_middleware(self):
        """Test creating app with middleware factories."""
        middleware_calls = []

        def fake_mw_factory(app):
            middleware_calls.append(app)

        app = create_app(middleware=[fake_mw_factory])
        assert len(middleware_calls) == 1
        assert middleware_calls[0] is app

    def test_create_app_without_fastapi_raises(self, monkeypatch):
        """Test ImportError when fastapi is not available."""
        original = sys.modules.get("fastapi")
        sys.modules["fastapi"] = None
        try:
            # Need to reload the module to trigger the import error
            import importlib
            import personal_index.api.server as server_mod
            with patch.dict(sys.modules, {"fastapi": None}):
                # Force re-import by removing cached module
                if "personal_index.api.server" in sys.modules:
                    del sys.modules["personal_index.api.server"]
                with pytest.raises(ImportError, match="fastapi is required"):
                    from personal_index.api.server import create_app as ca
                    ca()
        finally:
            if original is not None:
                sys.modules["fastapi"] = original
            else:
                sys.modules.pop("fastapi", None)
            # Restore cached module
            if "personal_index.api.server" not in sys.modules:
                importlib.reload(server_mod)


class TestLifespan:
    """Tests for the lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_loads_config(self):
        """Test that lifespan loads config on startup."""
        app = MagicMock()
        app.state = MagicMock()

        with patch("personal_index.api.server.load_config") as mock_load:
            mock_load.return_value = MagicMock()
            async_gen = lifespan(app)
            await async_gen.__aenter__()
            mock_load.assert_called_once()
            await async_gen.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_lifespan_sets_config_on_state(self):
        """Test that lifespan sets config on app.state."""
        app = MagicMock()
        app.state = MagicMock()

        test_config = MagicMock()
        with patch("personal_index.api.server.load_config", return_value=test_config):
            async_gen = lifespan(app)
            await async_gen.__aenter__()
            assert app.state.config is test_config
            await async_gen.__aexit__(None, None, None)


class TestCreateAppIntegration:
    """Integration tests for create_app."""

    def test_app_has_openapi_schema(self):
        """Test that the app generates an OpenAPI schema."""
        app = create_app()
        schema = app.openapi()
        assert "info" in schema
        assert schema["info"]["title"] == "Personal Index API"

    def test_app_has_routes(self):
        """Test that the app has default routes."""
        app = create_app()
        # FastAPI adds default routes like /docs, /openapi.json
        routes = [r.path for r in app.routes]
        assert "/docs" in routes or "/openapi.json" in routes
