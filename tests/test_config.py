"""Tests for configuration module."""

import json
import pytest
from pathlib import Path
from personal_index.config import (
    AppConfig,
    CrawlerConfig,
    Interest,
    ScheduleConfig,
)


class TestCrawlerConfig:
    def test_default_values(self):
        config = CrawlerConfig()
        assert config.max_depth == 3
        assert config.politeness_delay == 1.0
        assert config.rate_limit == 1.0
        assert config.max_pages_per_domain == 100
        assert config.timeout == 30
        assert config.respect_robots_txt is True

    def test_custom_values(self):
        config = CrawlerConfig(max_depth=5, rate_limit=2.0)
        assert config.max_depth == 5
        assert config.rate_limit == 2.0

    def test_to_dict(self):
        config = CrawlerConfig(max_depth=5)
        d = config.to_dict()
        assert d["max_depth"] == 5
        assert isinstance(d, dict)

    def test_from_dict(self):
        data = {"max_depth": 5, "rate_limit": 2.0}
        config = CrawlerConfig.from_dict(data)
        assert config.max_depth == 5
        assert config.rate_limit == 2.0


class TestInterest:
    def test_creation(self):
        interest = Interest(topic="AI", keywords=["neural", "deep learning"])
        assert interest.topic == "AI"
        assert interest.enabled is True
        assert interest.priority == 5

    def test_matches_with_keywords(self):
        interest = Interest(topic="AI", keywords=["neural", "deep learning"])
        assert interest.matches("This uses neural networks")
        assert interest.matches("Deep learning is great")
        assert not interest.matches("Nothing relevant here")

    def test_matches_disabled(self):
        interest = Interest(topic="AI", keywords=["neural"], enabled=False)
        assert not interest.matches("neural networks")

    def test_matches_case_insensitive(self):
        interest = Interest(topic="AI", keywords=["Neural"])
        assert interest.matches("neural networks")

    def test_matches_by_topic(self):
        interest = Interest(topic="machine learning")
        assert interest.matches("machine learning is fun")
        assert not interest.matches("something else")

    def test_to_dict_and_from_dict(self):
        interest = Interest(topic="AI", keywords=["neural"], priority=8)
        d = interest.to_dict()
        restored = Interest.from_dict(d)
        assert restored.topic == "AI"
        assert restored.keywords == ["neural"]
        assert restored.priority == 8


class TestScheduleConfig:
    def test_default_values(self):
        config = ScheduleConfig()
        assert config.enabled is False
        assert config.interval_hours == 24

    def test_to_dict(self):
        config = ScheduleConfig(enabled=True, interval_hours=12)
        d = config.to_dict()
        assert d["enabled"] is True
        assert d["interval_hours"] == 12


class TestAppConfig:
    def test_default_creation(self):
        config = AppConfig()
        assert len(config.interests) == 0
        assert config.crawler.max_depth == 3

    def test_ensure_dirs(self, tmp_path):
        config = AppConfig(
            config_dir=tmp_path / "config",
            data_dir=tmp_path / "data",
            index_dir=tmp_path / "index",
        )
        config.ensure_dirs()
        assert (tmp_path / "config").exists()
        assert (tmp_path / "data").exists()
        assert (tmp_path / "index").exists()

    def test_save_and_load(self, tmp_path):
        config_file = tmp_path / "test_config.json"
        config = AppConfig()
        config.interests.append(Interest(topic="AI", keywords=["neural"]))
        config.save(config_file)
        assert config_file.exists()

        loaded = AppConfig.load(config_file)
        assert len(loaded.interests) == 1
        assert loaded.interests[0].topic == "AI"

    def test_load_nonexistent(self, tmp_path):
        config_file = tmp_path / "nonexistent.json"
        config = AppConfig.load(config_file)
        assert isinstance(config, AppConfig)
        assert len(config.interests) == 0

    def test_to_dict(self):
        config = AppConfig()
        config.interests.append(Interest(topic="AI"))
        d = config.to_dict()
        assert "crawler" in d
        assert "interests" in d
        assert "schedule" in d
        assert len(d["interests"]) == 1
