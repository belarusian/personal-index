"""
Configuration management for personal-index.

Handles loading, saving, and validating user configuration
including interests, crawler settings, and schedule preferences.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/personal-index/config.json")


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler."""
    max_depth: int = 3
    politeness_delay: float = 1.0
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    max_page_size: int = 1024 * 1024  # 1MB
    user_agent: str = "personal-index/0.1.0"
    respect_robots_txt: bool = True


@dataclass
class ScheduleConfig:
    """Configuration for scheduled crawling."""
    enabled: bool = False
    interval_hours: int = 24
    max_pages_per_run: int = 100


@dataclass
class AppConfig:
    """Main application configuration."""
    config_dir: str = field(default_factory=lambda: os.path.expanduser("~/.config/personal-index"))
    data_dir: str = field(default_factory=lambda: os.path.expanduser("~/.local/share/personal-index"))
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        crawler_data = data.get("crawler", {})
        schedule_data = data.get("schedule", {})
        crawler = CrawlerConfig(**{k: v for k, v in crawler_data.items() if k in CrawlerConfig.__dataclass_fields__})
        schedule = ScheduleConfig(**{k: v for k, v in schedule_data.items() if k in ScheduleConfig.__dataclass_fields__})
        return cls(
            config_dir=data.get("config_dir", cls().config_dir),
            data_dir=data.get("data_dir", cls().data_dir),
            crawler=crawler,
            schedule=schedule,
        )


class ConfigManager:
    """Manages loading and saving application configuration."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._config: Optional[AppConfig] = None

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> AppConfig:
        """Load configuration from file, or return defaults."""
        path = Path(self.config_path)
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self._config = AppConfig.from_dict(data)
                return self._config
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not parse config: {e}. Using defaults.")
        self._config = AppConfig()
        return self._config

    def save(self, config: Optional[AppConfig] = None) -> None:
        """Save configuration to file."""
        if config is None:
            config = self.config
        path = Path(self.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

    def ensure_dirs(self) -> None:
        """Ensure all required directories exist."""
        Path(self.config.config_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)
