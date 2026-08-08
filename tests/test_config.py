"""Tests for personal_index.config."""

import pytest
import tempfile
import shutil
from pathlib import Path

from personal_index.config import AppConfig, ConfigManager


class TestAppConfig:
    def test_default_config(self):
        config = AppConfig()
        assert config.data_dir == "~/.personal-index"
        assert config.default_crawl_depth == 2
        assert config.default_max_pages == 100
        assert config.default_rate_limit == 1.0
        assert config.respect_robots is True

    def test_custom_config(self):
        config = AppConfig(
            data_dir="/custom/path",
            default_crawl_depth=5,
            default_max_pages=500,
        )
        assert config.data_dir == "/custom/path"
        assert config.default_crawl_depth == 5
        assert config.default_max_pages == 500

    def test_search_index_dir_default(self):
        config = AppConfig(data_dir="/test")
        assert "test" in config.search_index_dir
        assert "index" in config.search_index_dir


@pytest.fixture
def temp_config_file():
    """Create a temporary config file path."""
    tmpdir = tempfile.mkdtemp()
    config_file = Path(tmpdir) / "config.json"
    yield config_file
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestConfigManager:
    def test_default_config(self, temp_config_file):
        manager = ConfigManager(config_file=str(temp_config_file))
        assert manager.get("default_crawl_depth") == 2

    def test_set_and_get(self, temp_config_file):
        manager = ConfigManager(config_file=str(temp_config_file))
        manager.set("default_crawl_depth", 5)
        assert manager.get("default_crawl_depth") == 5

    def test_save_and_load(self, temp_config_file):
        manager = ConfigManager(config_file=str(temp_config_file))
        manager.set("default_crawl_depth", 5)
        manager.set("default_max_pages", 200)
        manager.save()

        manager2 = ConfigManager(config_file=str(temp_config_file))
        assert manager2.get("default_crawl_depth") == 5
        assert manager2.get("default_max_pages") == 200

    def test_reset(self, temp_config_file):
        manager = ConfigManager(config_file=str(temp_config_file))
        manager.set("default_crawl_depth", 5)
        manager.save()
        manager.reset()
        assert manager.get("default_crawl_depth") == 2

    def test_as_dict(self, temp_config_file):
        manager = ConfigManager(config_file=str(temp_config_file))
        config_dict = manager.as_dict()
        assert isinstance(config_dict, dict)
        assert "default_crawl_depth" in config_dict

    def test_set_unknown_key(self, temp_config_file):
        manager = ConfigManager(config_file=str(temp_config_file))
        with pytest.raises(AttributeError, match="Unknown config key"):
            manager.set("nonexistent_key", "value")

    def test_get_with_default(self, temp_config_file):
        manager = ConfigManager(config_file=str(temp_config_file))
        assert manager.get("nonexistent_key", "default_value") == "default_value"

    def test_load_invalid_json(self, temp_config_file):
        """Test handling of corrupted config file."""
        temp_config_file.write_text("not valid json{{{")
        manager = ConfigManager(config_file=str(temp_config_file))
        # Should fall back to defaults
        assert manager.get("default_crawl_depth") == 2
