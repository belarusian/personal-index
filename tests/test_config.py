"""Tests for configuration management."""

import json
import pytest
from pathlib import Path
from personal_index.config import (
    AppConfig,
    CrawlerConfig,
    Interest,
    SchedulerConfig,
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
        config = CrawlerConfig(max_depth=5, politeness_delay=2.0)
        assert config.max_depth == 5
        assert config.politeness_delay == 2.0

    def test_to_dict(self):
        config = CrawlerConfig(max_depth=5)
        data = config.to_dict()
        assert data["max_depth"] == 5
        assert isinstance(data, dict)

    def test_from_dict(self):
        data = {"max_depth": 5, "politeness_delay": 2.0}
        config = CrawlerConfig.from_dict(data)
        assert config.max_depth == 5
        assert config.politeness_delay == 2.0


class TestInterest:
    def test_create_interest(self):
        interest = Interest(topic="machine learning")
        assert interest.topic == "machine learning"
        assert interest.keywords == []
        assert interest.enabled is True
        assert interest.priority == 5

    def test_create_interest_with_keywords(self):
        interest = Interest(
            topic="AI",
            keywords=["neural networks", "deep learning"],
            priority=8,
        )
        assert interest.topic == "AI"
        assert len(interest.keywords) == 2
        assert interest.priority == 8

    def test_to_dict(self):
        interest = Interest(topic="AI", keywords=["ml"])
        data = interest.to_dict()
        assert data["topic"] == "AI"
        assert data["keywords"] == ["ml"]

    def test_from_dict(self):
        data = {"topic": "AI", "keywords": ["ml"], "enabled": True, "priority": 8}
        interest = Interest.from_dict(data)
        assert interest.topic == "AI"
        assert interest.priority == 8


class TestSchedulerConfig:
    def test_default_values(self):
        config = SchedulerConfig()
        assert config.enabled is False
        assert config.interval_hours == 24

    def test_custom_values(self):
        config = SchedulerConfig(enabled=True, interval_hours=12)
        assert config.enabled is True
        assert config.interval_hours == 12


class TestAppConfig:
    def test_default_config(self):
        config = AppConfig()
        assert len(config.interests) == 0
        assert config.crawler.max_depth == 3

    def test_save_and_load(self, tmp_path: Path):
        config_dir = tmp_path / "config"
        config = AppConfig(config_dir=config_dir)
        config.interests.append(Interest(topic="test"))
        config.save()

        loaded = AppConfig.load(config_dir / "config.json")
        assert len(loaded.interests) == 1
        assert loaded.interests[0].topic == "test"

    def test_load_nonexistent(self):
        config = AppConfig.load(Path("/nonexistent/config.json"))
        assert config is not None
        assert len(config.interests) == 0
