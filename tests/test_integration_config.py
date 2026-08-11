"""Integration tests for configuration management."""

from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from personal_index.app import PersonalIndexApp
from personal_index.config.loader import load_config, save_config
from personal_index.config.models import AppConfig, CrawlerConfig, IndexConfig, SchedulerConfig


class TestConfigIntegration:
    """Test configuration loading and saving."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, "config.yaml")

    def test_load_default_config(self):
        """Loading a valid config should return AppConfig."""
        config_data = {
            "data_dir": ".personal_index",
            "crawler": {"max_depth": 5, "politeness_delay": 1.0, "rate_limit": 10,
                        "respect_robots_txt": True, "timeout": 30},
            "scheduler": {"enabled": False, "interval_hours": 24},
            "index": {"enable_stemming": True, "index_path": ".personal_index"},
            "interests": [],
        }
        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

        cfg = load_config(self.config_path)
        assert isinstance(cfg, AppConfig)
        assert cfg.crawler.max_depth == 5

    def test_save_and_reload_config(self):
        """Saved config should reload correctly."""
        cfg = AppConfig(
            data_dir=".test_data",
            crawler=CrawlerConfig(max_depth=10, politeness_delay=2.0),
            scheduler=SchedulerConfig(enabled=True, interval_hours=12),
            index=IndexConfig(enable_stemming=False),
        )
        save_config(cfg, self.config_path)

        reloaded = load_config(self.config_path)
        assert reloaded.crawler.max_depth == 10
        assert reloaded.scheduler.enabled is True
        assert reloaded.index.enable_stemming is False

    def test_app_uses_config(self):
        """App should use configuration values."""
        config_data = {
            "data_dir": os.path.join(self.tmpdir, "data"),
            "crawler": {"max_depth": 3, "politeness_delay": 0.5, "rate_limit": 5,
                        "respect_robots_txt": True, "timeout": 15},
            "scheduler": {"enabled": True, "interval_hours": 6},
            "index": {"enable_stemming": True, "index_path": os.path.join(self.tmpdir, "data")},
            "interests": [],
        }
        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

        app = PersonalIndexApp(config_path=self.config_path)
        app.initialize()
        assert app.config.crawler.max_depth == 3
        assert app.config.scheduler.enabled is True

    def test_config_fallback_on_missing_file(self):
        """App should use defaults when config file is missing."""
        app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "nonexistent.yaml"),
            data_dir=self.tmpdir,
        )
        app.initialize()
        assert app.config.crawler.max_depth == 3  # default

    def test_save_config_creates_file(self):
        """save_config should create the file if it doesn't exist."""
        new_path = os.path.join(self.tmpdir, "new_config.yaml")
        cfg = AppConfig(
            data_dir=self.tmpdir,
            crawler=CrawlerConfig(),
            scheduler=SchedulerConfig(),
            index=IndexConfig(),
        )
        save_config(cfg, new_path)
        assert os.path.exists(new_path)
        with open(new_path) as f:
            data = yaml.safe_load(f)
        assert "crawler" in data
