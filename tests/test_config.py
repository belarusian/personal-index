"""Tests for the configuration module."""

import json
import os
import tempfile
import pytest
from personal_index.config import (
    AppConfig,
    CrawlerConfig,
    ScheduleConfig,
    ConfigManager,
)


class TestCrawlerConfig:
    def test_default_values(self):
        config = CrawlerConfig()
        assert config.max_depth == 3
        assert config.politeness_delay == 1.0
        assert config.max_concurrent_requests == 5
        assert config.respect_robots_txt is True

    def test_custom_values(self):
        config = CrawlerConfig(max_depth=5, politeness_delay=2.0)
        assert config.max_depth == 5
        assert config.politeness_delay == 2.0


class TestScheduleConfig:
    def test_default_values(self):
        config = ScheduleConfig()
        assert config.enabled is False
        assert config.interval_hours == 24
        assert config.max_pages_per_run == 100


class TestAppConfig:
    def test_default_values(self):
        config = AppConfig()
        assert isinstance(config.crawler, CrawlerConfig)
        assert isinstance(config.schedule, ScheduleConfig)

    def test_to_dict(self):
        config = AppConfig()
        data = config.to_dict()
        assert "crawler" in data
        assert "schedule" in data
        assert data["crawler"]["max_depth"] == 3

    def test_from_dict(self):
        data = {
            "crawler": {"max_depth": 5, "politeness_delay": 2.0},
            "schedule": {"enabled": True, "interval_hours": 12},
        }
        config = AppConfig.from_dict(data)
        assert config.crawler.max_depth == 5
        assert config.schedule.enabled is True


class TestConfigManager:
    def test_load_default_config(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        manager = ConfigManager(config_path=config_path)
        config = manager.load()
        assert config.crawler.max_depth == 3

    def test_save_and_load(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        manager = ConfigManager(config_path=config_path)
        config = AppConfig()
        config.crawler.max_depth = 10
        manager.save(config)

        manager2 = ConfigManager(config_path=config_path)
        loaded = manager2.load()
        assert loaded.crawler.max_depth == 10

    def test_ensure_dirs(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        manager = ConfigManager(config_path=config_path)
        config = AppConfig(
            config_dir=str(tmp_path / "custom_config"),
            data_dir=str(tmp_path / "custom_data"),
        )
        manager.save(config)
        manager.ensure_dirs()
        assert os.path.isdir(str(tmp_path / "custom_config"))
        assert os.path.isdir(str(tmp_path / "custom_data"))

    def test_load_invalid_json(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        with open(config_path, "w") as f:
            f.write("not valid json")
        manager = ConfigManager(config_path=config_path)
        config = manager.load()
        assert config.crawler.max_depth == 3  # Falls back to defaults
