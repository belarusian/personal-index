"""Tests for configuration models."""

import pytest
from personal_index.config.models import (
    Interest,
    CrawlerConfig,
    SchedulerConfig,
    IndexConfig,
    AppConfig,
    MatchMode,
)


class TestInterest:
    def test_create_interest_defaults(self):
        interest = Interest(name="python")
        assert interest.name == "python"
        assert interest.keywords == []
        assert interest.url_patterns == []
        assert interest.match_mode == MatchMode.ANY
        assert interest.priority == 5
        assert interest.enabled is True

    def test_create_interest_with_keywords(self):
        interest = Interest(name="python", keywords=["python", "programming"])
        assert interest.keywords == ["python", "programming"]

    def test_priority_clamped_min(self):
        interest = Interest(name="test", priority=0)
        assert interest.priority == 1

    def test_priority_clamped_max(self):
        interest = Interest(name="test", priority=20)
        assert interest.priority == 10

    def test_interest_enabled_flag(self):
        interest = Interest(name="test", enabled=False)
        assert not interest.enabled


class TestCrawlerConfig:
    def test_defaults(self):
        cfg = CrawlerConfig()
        assert cfg.max_depth == 3
        assert cfg.politeness_delay == 1.0
        assert cfg.rate_limit == 10
        assert cfg.timeout == 30
        assert cfg.respect_robots_txt is True

    def test_custom_config(self):
        cfg = CrawlerConfig(max_depth=5, politeness_delay=2.0)
        assert cfg.max_depth == 5
        assert cfg.politeness_delay == 2.0


class TestSchedulerConfig:
    def test_defaults(self):
        cfg = SchedulerConfig()
        assert cfg.enabled is False
        assert cfg.interval_hours == 24


class TestIndexConfig:
    def test_defaults(self):
        cfg = IndexConfig()
        assert cfg.index_path == ".personal_index"
        assert cfg.enable_stemming is True


class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.data_dir == ".personal_index"
        assert cfg.interests == []

    def test_with_interests(self):
        interest = Interest(name="python")
        cfg = AppConfig(interests=[interest])
        assert len(cfg.interests) == 1
        assert cfg.interests[0].name == "python"


class TestMatchMode:
    def test_values(self):
        assert MatchMode.ANY.value == "any"
        assert MatchMode.ALL.value == "all"
        assert MatchMode.REGEX.value == "regex"
