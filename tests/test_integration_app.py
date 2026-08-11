"""Integration tests for the PersonalIndexApp factory."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp


class TestAppFactory:
    """Test the PersonalIndexApp factory pattern."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )

    def test_singleton_components(self):
        """Components should be singletons within an app instance."""
        self.app.initialize()
        assert self.app.search_index is self.app.search_index
        assert self.app.interest_store is self.app.interest_store
        assert self.app.pipeline is self.app.pipeline

    def test_lazy_initialization(self):
        """Components should be lazily initialized."""
        assert self.app._search_index is None
        _ = self.app.search_index
        assert self.app._search_index is not None

    def test_initialize_is_idempotent(self):
        """Calling initialize multiple times should be safe."""
        self.app.initialize()
        self.app.initialize()
        assert self.app._initialized is True

    def test_shutdown_is_safe(self):
        """Calling shutdown should not raise."""
        self.app.initialize()
        self.app.shutdown()
        self.app.shutdown()  # Should not raise

    def test_process_content_returns_dict(self):
        """process_content should always return a dict."""
        self.app.initialize()
        result = self.app.process_content("https://x.com", "test", "Title")
        assert isinstance(result, dict)

    def test_process_content_preserves_url(self):
        """process_content should preserve the URL."""
        self.app.initialize()
        result = self.app.process_content("https://example.com/test", "content", "Title")
        assert result["url"] == "https://example.com/test"

    def test_process_content_preserves_title(self):
        """process_content should preserve the title."""
        self.app.initialize()
        result = self.app.process_content("https://x.com", "content", "My Title")
        assert result["title"] == "My Title"

    def test_search_returns_list(self):
        """search should always return a list."""
        self.app.initialize()
        results = self.app.search("test")
        assert isinstance(results, list)

    def test_get_stats_returns_dict(self):
        """get_stats should return a dict."""
        self.app.initialize()
        stats = self.app.get_stats()
        assert isinstance(stats, dict)

    def test_add_interest_persists(self):
        """add_interest should persist to the store."""
        self.app.initialize()
        self.app.add_interest("Test", keywords=["test"])
        interests = self.app.interest_store.list_all()
        assert any(i.name == "Test" for i in interests)

    def test_config_property(self):
        """config property should return AppConfig."""
        from personal_index.config.models import AppConfig
        self.app.initialize()
        assert isinstance(self.app.config, AppConfig)

    def test_data_dir_created(self):
        """initialize should create the data directory."""
        data_dir = os.path.join(self.tmpdir, "new_data")
        app = PersonalIndexApp(data_dir=data_dir)
        app.initialize()
        assert os.path.isdir(data_dir)
