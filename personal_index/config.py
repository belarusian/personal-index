"""Configuration management for personal-index."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "personal-index"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


@dataclass
class Interest:
    """Represents a user-defined interest to track."""

    topic: str
    keywords: list[str] = field(default_factory=list)
    url_patterns: list[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Interest":
        return cls(**data)


@dataclass
class CrawlConfig:
    """Configuration for the web crawler."""

    max_depth: int = 3
    politeness_delay: float = 1.0
    rate_limit: float = 1.0
    max_pages_per_domain: int = 100
    user_agent: str = "PersonalIndex/0.1.0"
    respect_robots_txt: bool = True
    timeout: int = 30

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlConfig":
        return cls(**data)


@dataclass
class SchedulerConfig:
    """Configuration for scheduled crawling."""

    enabled: bool = False
    interval_hours: int = 24
    last_run: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SchedulerConfig":
        return cls(**data)


@dataclass
class AppConfig:
    """Main application configuration."""

    interests: list[Interest] = field(default_factory=list)
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    index_path: str = str(Path.home() / ".config" / "personal-index" / "index")

    def to_dict(self) -> dict:
        return {
            "interests": [i.to_dict() for i in self.interests],
            "crawl": self.crawl.to_dict(),
            "scheduler": self.scheduler.to_dict(),
            "index_path": self.index_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        interests = [Interest.from_dict(i) for i in data.get("interests", [])]
        crawl = CrawlConfig.from_dict(data.get("crawl", {}))
        scheduler = SchedulerConfig.from_dict(data.get("scheduler", {}))
        return cls(
            interests=interests,
            crawl=crawl,
            scheduler=scheduler,
            index_path=data.get("index_path", cls().index_path),
        )


class ConfigManager:
    """Manages loading and saving configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE

    def load(self) -> AppConfig:
        """Load configuration from file."""
        if not self.config_path.exists():
            return AppConfig()
        with open(self.config_path, "r") as f:
            data = json.load(f)
        return AppConfig.from_dict(data)

    def save(self, config: AppConfig) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

    def add_interest(self, config: AppConfig, interest: Interest) -> AppConfig:
        """Add a new interest to the configuration."""
        config.interests.append(interest)
        self.save(config)
        return config

    def remove_interest(self, config: AppConfig, topic: str) -> AppConfig:
        """Remove an interest by topic name."""
        config.interests = [i for i in config.interests if i.topic != topic]
        self.save(config)
        return config

    def get_interest(self, config: AppConfig, topic: str) -> Optional[Interest]:
        """Get an interest by topic name."""
        for interest in config.interests:
            if interest.topic == topic:
                return interest
        return None
