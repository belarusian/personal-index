"""Tests for configuration management."""

import json
import pytest
from pathlib import Path
from personal_index.config import (
    Interest,
    CrawlConfig,
    SchedulerConfig,
    AppConfig,
    ConfigManager,
)


class TestInterest:
    def test_create_interest_defaults(self):
        interest = Interest(topic="python")
        assert interest.topic == "python"
        assert interest.keywords == []
        assert interest.url_patterns == []
        assert interest.enabled is True

    def test_create_interest_with_keywords(self):
        interest = Interest(topic="python", keywords=["programming", "coding"])
        assert interest.keywords == ["programming", "coding"]

    def test_interest_to_dict(self):
        interest = Interest(topic="python", keywords=["coding"])
        data = interest.to_dict()
        assert data["topic"] == "python"
        assert data["keywords"] == ["coding"]

    def test_interest_from_dict(self):
        data = {"topic": "python", "keywords": ["coding"], "url_patterns": [], "enabled": True}
        interest = Interest.from_dict(data)
        assert interest.topic == "python"
        assert interest.keywords == ["coding"]


class TestCrawlConfig:
    def test_default_crawl_config(self):
        config = CrawlConfig()
        assert config.max_depth == 3
        assert config.politeness_delay == 1.0
        assert config.rate_limit == 1.0

    def test_custom_crawl_config(self):
        config = CrawlConfig(max_depth=5, politeness_delay=2.0)
        assert config.max_depth == 5
        assert config.politeness_delay == 2.0

    def test_crawl_config_to_dict(self):
        config = CrawlConfig(max_depth=5)
        data = config.to_dict()
        assert data["max_depth"] == 5

    def test_crawl_config_from_dict(self):
        data = {"max_depth": 5, "politeness_delay": 2.0, "rate_limit": 1.0,
                "max_pages_per_domain": 100, "user_agent": "Test/1.0",
                "respect_robots_txt": True, "timeout": 30}
        config = CrawlConfig.from_dict(data)
        assert config.max_depth == 5


class TestSchedulerConfig:
    def test_default_scheduler_config(self):
        config = SchedulerConfig()
        assert config.enabled is False
        assert config.interval_hours == 24

    def test_scheduler_to_from_dict(self):
        config = SchedulerConfig(enabled=True, interval_hours=12)
        data = config.to_dict()
        restored = SchedulerConfig.from_dict(data)
        assert restored.enabled is True
        assert restored.interval_hours == 12


class TestAppConfig:
    def test_default_app_config(self):
        config = AppConfig()
        assert config.interests == []
        assert config.crawl.max_depth == 3

    def test_app_config_with_interests(self):
        interest = Interest(topic="python")
        config = AppConfig(interests=[interest])
        assert len(config.interests) == 1

    def test_app_config_to_from_dict(self):
        interest = Interest(topic="python", keywords=["coding"])
        config = AppConfig(interests=[interest])
        data = config.to_dict()
        restored = AppConfig.from_dict(data)
        assert len(restored.interests) == 1
        assert restored.interests[0].topic == "python"


class TestConfigManager:
    def test_load_creates_default_when_no_file(self, tmp_path):
        manager = ConfigManager(config_path=tmp_path / "nonexistent.json")
        config = manager.load()
        assert isinstance(config, AppConfig)

    def test_save_and_load(self, tmp_path):
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)
        config = AppConfig()
        config.interests.append(Interest(topic="python"))
        manager.save(config)
        loaded = manager.load()
        assert len(loaded.interests) == 1
        assert loaded.interests[0].topic == "python"

    def test_add_interest(self, tmp_path):
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)
        config = AppConfig()
        manager.add_interest(config, Interest(topic="python"))
        assert len(config.interests) == 1

    def test_remove_interest(self, tmp_path):
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)
        config = AppConfig(interests=[Interest(topic="python"), Interest(topic="rust")])
        manager.remove_interest(config, "python")
        assert len(config.interests) == 1
        assert config.interests[0].topic == "rust"

    def test_get_interest(self, tmp_path):
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)
        config = AppConfig(interests=[Interest(topic="python")])
        interest = manager.get_interest(config, "python")
        assert interest is not None
        assert interest.topic == "python"

    def test_get_interest_not_found(self, tmp_path):
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)
        config = AppConfig()
        interest = manager.get_interest(config, "nonexistent")
        assert interest is None
