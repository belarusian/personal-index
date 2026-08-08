"""Tests for API server module."""

from __future__ import annotations

import pytest

from personal_index.api.server import create_app


@pytest.fixture
def app():
    """Create a test app instance."""
    return create_app()


class TestCreateApp:
    """Tests for create_app factory."""

    def test_create_app_returns_fastapi(self, app):
        """Test that create_app returns a FastAPI instance."""
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_create_app_has_title(self, app):
        """Test that app has correct title."""
        assert app.title == "Personal Index API"

    def test_create_app_has_version(self, app):
        """Test that app has version set."""
        assert app.version == "0.1.0"

    def test_create_app_with_config(self):
        """Test creating app with custom config."""
        from personal_index.config.models import AppConfig
        config = AppConfig()
        app = create_app(config=config)
        assert app.state.config == config

    def test_create_app_without_fastapi(self, monkeypatch):
        """Test ImportError when fastapi is not available."""
        import sys
        original = sys.modules.get("fastapi")
        sys.modules["fastapi"] = None
        try:
            with pytest.raises(ImportError, match="fastapi is required"):
                create_app()
        finally:
            if original is not None:
                sys.modules["fastapi"] = original
            else:
                sys.modules.pop("fastapi", None)
