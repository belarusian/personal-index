"""Tests for personal_index.config."""

import json
import pytest

from personal_index.config import AppConfig, ConfigManager


@pytest.fixture
def config_path(tmp_path):
    return str(tmp_path / "test_config_dir")


@pytest.fixture
def manager(config_path):
    return ConfigManager(data_dir=config_path)


class TestAppConfig:
    """Tests for AppConfig."""

    def test_defaults(self):
        config = AppConfig()
        assert config.max_concurrent_requests == 5
        assert config.default_crawl_delay == 1.0
        assert config.default_crawl_depth == 3
        assert config.respect_robots is True
        assert config.log_level == "INFO"

    def test_custom_values(self):
        config = AppConfig(
            max_concurrent_requests=10,
            default_crawl_delay=2.0,
            log_level="DEBUG",
        )
        assert config.max_concurrent_requests == 10
        assert config.default_crawl_delay == 2.0
        assert config.log_level == "DEBUG"


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_new_manager_defaults(self, manager):
        config = manager.config
        assert config.max_concurrent_requests == 5
        assert config.respect_robots is True

    def test_get_value(self, manager):
        assert manager.get("max_concurrent_requests") == 5

    def test_get_nonexistent(self, manager):
        assert manager.get("nonexistent", "default") == "default"

    def test_set_value(self, manager):
        assert manager.set("max_concurrent_requests", 10) is True
        assert manager.config.max_concurrent_requests == 10

    def test_set_nonexistent(self, manager):
        assert manager.set("nonexistent", 5) is False

    def test_update_multiple(self, manager):
        manager.update(
            max_concurrent_requests=10,
            default_crawl_delay=2.0,
            log_level="DEBUG",
        )
        assert manager.config.max_concurrent_requests == 10
        assert manager.config.default_crawl_delay == 2.0
        assert manager.config.log_level == "DEBUG"

    def test_reset(self, manager):
        manager.set("max_concurrent_requests", 10)
        manager.reset()
        assert manager.config.max_concurrent_requests == 5

    def test_to_dict(self, manager):
        d = manager.to_dict()
        assert isinstance(d, dict)
        assert "max_concurrent_requests" in d

    def test_persistence(self, config_path):
        m1 = ConfigManager(data_dir=config_path)
        m1.set("max_concurrent_requests", 15)

        m2 = ConfigManager(data_dir=config_path)
        assert m2.config.max_concurrent_requests == 15

    def test_export(self, manager, tmp_path):
        export_path = str(tmp_path / "exported.json")
        manager.export(export_path)
        assert Path(export_path).exists()
        data = json.loads(Path(export_path).read_text())
        assert "max_concurrent_requests" in data

    def test_from_dict(self, config_path):
        data = {
            "max_concurrent_requests": 20,
            "default_crawl_delay": 3.0,
        }
        manager = ConfigManager.from_dict(data, data_dir=config_path)
        assert manager.config.max_concurrent_requests == 20
        assert manager.config.default_crawl_delay == 3.0

    def test_corrupted_config(self, config_path):
        config_file = Path(config_path) / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("not valid json{{{")
        manager = ConfigManager(data_dir=config_path)
        assert manager.config.max_concurrent_requests == 5  # defaults

    def test_data_dir_property(self, manager):
        assert manager.data_dir == manager._data_dir
