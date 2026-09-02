"""Configuration management for personal-index."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from personal_index.models import CrawlConfig, Interest

# Alias for backward compatibility
CrawlerConfig = CrawlConfig


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    enabled: bool = False
    interval_hours: int = 24

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SchedulerConfig:
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class AppConfig:
    """Application configuration."""
    interests: list[Interest] = field(default_factory=list)
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    schedule: SchedulerConfig = field(default_factory=SchedulerConfig)
    config_dir: str | None = None
    index_dir: str | None = None
    crawler: CrawlConfig | None = None

    def __post_init__(self):
        # Default crawler to crawl if not set
        if self.crawler is None:
            self.crawler = self.crawl

    def to_dict(self) -> dict:
        return {
            "interests": [i.to_dict() for i in self.interests],
            "crawl": self.crawl.to_dict(),
            "schedule": self.schedule.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        interests = [Interest.from_dict(d) for d in data.get("interests", [])]
        crawl = CrawlConfig.from_dict(data.get("crawl", {}))
        schedule = SchedulerConfig.from_dict(data.get("schedule", {}))
        return cls(interests=interests, crawl=crawl, schedule=schedule)

    def save(self):
        """Save config to disk."""
        if not self.config_dir:
            return
        path = Path(self.config_dir) / "config.json"
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, config_path: Path) -> AppConfig:
        """Load config from disk."""
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return cls()
            return cls.from_dict(data)
        return cls()


class ConfigManager:
    """Manages loading and saving configuration."""

    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load(self) -> AppConfig:
        """Load config, creating default if file doesn't exist."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return AppConfig()
            return AppConfig.from_dict(data)
        return AppConfig()

    def save(self, config: AppConfig):
        """Save config to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

    def add_interest(self, config: AppConfig, interest: Interest):
        """Add an interest to the config."""
        config.interests.append(interest)

    def remove_interest(self, config: AppConfig, topic: str):
        """Remove an interest by topic."""
        config.interests = [i for i in config.interests if i.topic != topic]

    def get_interest(self, config: AppConfig, topic: str) -> Interest | None:
        """Get an interest by topic."""
        for interest in config.interests:
            if interest.topic == topic:
                return interest
        return None
