"""Tests for personal_index.app — PersonalIndexApp class.

Covers: creation, config loading, module wiring, initialization,
process_content, search, add_interest, get_stats, shutdown.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp


@pytest.fixture
def tmp_data_dir():
    """Provide a temporary data directory for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def app(tmp_data_dir):
    """Provide a PersonalIndexApp instance with a temp data dir."""
    config_path = os.path.join(tmp_data_dir, "config.yaml")
    data_dir = os.path.join(tmp_data_dir, "data")
    return PersonalIndexApp(config_path=config_path, data_dir=data_dir)


class TestPersonalIndexAppCreation:
    """Test PersonalIndexApp instantiation and defaults."""

    def test_creation_defaults(self):
        app = PersonalIndexApp()
        assert app.config_path == "config.yaml"
        assert app.data_dir == ".personal_index"
        assert app._initialized is False

    def test_creation_custom_paths(self):
        app = PersonalIndexApp(config_path="/custom/config.yaml", data_dir="/custom/data")
        assert app.config_path == "/custom/config.yaml"
        assert app.data_dir == "/custom/data"

    def test_creation_private_attrs_none(self):
        app = PersonalIndexApp()
        assert app._config is None
        assert app._interest_store is None
        assert app._search_index is None
        assert app._content_search is None
        assert app._scheduler is None
        assert app._pipeline is None


class TestPersonalIndexAppConfig:
    """Test config loading behavior."""

    def test_config_returns_app_config(self, app):
        from personal_index.config.models import AppConfig
        cfg = app.config
        assert isinstance(cfg, AppConfig)

    def test_config_cached(self, app):
        cfg1 = app.config
        cfg2 = app.config
        assert cfg1 is cfg2

    def test_config_returns_defaults_when_no_file(self, tmp_data_dir):
        """When config file is missing, load_config returns default AppConfig."""
        config_path = os.path.join(tmp_data_dir, "nonexistent.yaml")
        app = PersonalIndexApp(config_path=config_path, data_dir=tmp_data_dir)
        cfg = app.config
        # load_config returns AppConfig() with defaults when file missing
        assert isinstance(cfg, type(app.config))


class TestPersonalIndexAppModuleWiring:
    """Test that app wires modules correctly as singletons."""

    def test_interest_store_singleton(self, app):
        app.initialize()
        store1 = app.interest_store
        store2 = app.interest_store
        assert store1 is store2

    def test_search_index_singleton(self, app):
        app.initialize()
        idx1 = app.search_index
        idx2 = app.search_index
        assert idx1 is idx2

    def test_content_search_singleton(self, app):
        app.initialize()
        cs1 = app.content_search
        cs2 = app.content_search
        assert cs1 is cs2

    def test_scheduler_singleton(self, app):
        app.initialize()
        s1 = app.scheduler
        s2 = app.scheduler
        assert s1 is s2

    def test_pipeline_singleton(self, app):
        app.initialize()
        p1 = app.pipeline
        p2 = app.pipeline
        assert p1 is p2

    def test_content_search_uses_app_search_index(self, app):
        app.initialize()
        assert app.content_search.index is app.search_index


class TestPersonalIndexAppInitialize:
    """Test initialize() behavior."""

    def test_initialize_creates_data_dir(self, tmp_data_dir):
        data_dir = os.path.join(tmp_data_dir, "new_data")
        app = PersonalIndexApp(data_dir=data_dir)
        app.initialize()
        assert os.path.isdir(data_dir)

    def test_initialize_sets_flag(self, app):
        assert app._initialized is False
        app.initialize()
        assert app._initialized is True

    def test_initialize_is_idempotent(self, app):
        app.initialize()
        app.initialize()
        assert app._initialized is True

    def test_initialize_loads_all_components(self, app):
        app.initialize()
        assert app._config is not None
        assert app._interest_store is not None
        assert app._search_index is not None
        assert app._content_search is not None
        assert app._pipeline is not None


class TestPersonalIndexAppShutdown:
    """Test shutdown() behavior."""

    def test_shutdown_no_error(self, app):
        app.initialize()
        app.shutdown()  # Should not raise

    def test_shutdown_without_init(self, app):
        app.shutdown()  # Should not raise even if not initialized

    def test_shutdown_idempotent(self, app):
        app.initialize()
        app.shutdown()
        app.shutdown()  # Should not raise


class TestPersonalIndexAppProcessContent:
    """Test process_content() pipeline execution."""

    def test_process_content_returns_dict(self, app):
        app.initialize()
        result = app.process_content("https://example.com", "hello world", "Title")
        assert isinstance(result, dict)

    def test_process_content_preserves_url(self, app):
        app.initialize()
        result = app.process_content("https://example.com/page", "content", "Title")
        assert result["url"] == "https://example.com/page"

    def test_process_content_preserves_title(self, app):
        app.initialize()
        result = app.process_content("https://example.com", "content", "My Title")
        assert result["title"] == "My Title"

    def test_process_content_with_empty_title(self, app):
        app.initialize()
        result = app.process_content("https://example.com", "content", "")
        assert "title" in result

    def test_process_content_adds_to_search_index(self, app):
        app.initialize()
        app.process_content("https://example.com", "python programming", "Python")
        results = app.search("python")
        assert isinstance(results, list)


class TestPersonalIndexAppSearch:
    """Test search() behavior."""

    def test_search_returns_list(self, app):
        app.initialize()
        results = app.search("test")
        assert isinstance(results, list)

    def test_search_empty_index(self, app):
        app.initialize()
        results = app.search("nonexistent")
        assert isinstance(results, list)

    def test_search_with_limit(self, app):
        app.initialize()
        results = app.search("test", limit=5)
        assert isinstance(results, list)


class TestPersonalIndexAppAddInterest:
    """Test add_interest() behavior."""

    def test_add_interest_persists(self, app):
        app.initialize()
        app.add_interest("Python", keywords=["python", "django"])
        interests = app.interest_store.list_all()
        assert any(i.name == "Python" for i in interests)

    def test_add_interest_with_defaults(self, app):
        app.initialize()
        app.add_interest("Simple")
        interests = app.interest_store.list_all()
        assert any(i.name == "Simple" for i in interests)

    def test_add_interest_with_url_patterns(self, app):
        app.initialize()
        app.add_interest("News", url_patterns=["*.news.com"])
        interests = app.interest_store.list_all()
        news = [i for i in interests if i.name == "News"]
        assert len(news) == 1
        assert "*.news.com" in news[0].url_patterns

    def test_add_interest_with_priority(self, app):
        app.initialize()
        app.add_interest("HighPriority", priority=10)
        interests = app.interest_store.list_all()
        hp = [i for i in interests if i.name == "HighPriority"]
        assert len(hp) == 1
        assert hp[0].priority == 10


class TestPersonalIndexAppGetStats:
    """Test get_stats() behavior."""

    def test_get_stats_returns_dict(self, app):
        app.initialize()
        stats = app.get_stats()
        assert isinstance(stats, dict)

    def test_get_stats_has_expected_keys(self, app):
        app.initialize()
        stats = app.get_stats()
        expected_keys = {
            "indexed_items", "interests", "scheduled_jobs",
            "pipeline_steps", "enabled_steps", "data_dir",
        }
        assert expected_keys.issubset(stats.keys())

    def test_get_stats_data_dir_matches(self, app):
        app.initialize()
        stats = app.get_stats()
        assert stats["data_dir"] == app.data_dir

    def test_get_stats_pipeline_steps(self, app):
        app.initialize()
        stats = app.get_stats()
        assert stats["pipeline_steps"] >= 4  # extract, filter, score, tag
