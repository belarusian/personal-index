"""Configuration management for Personal Index."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "personal_index"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_INDEX_DIR = Path.home() / ".local" / "share" / "personal_index"


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler."""

    max_depth: int = 3
    politeness_delay: float = 1.0
    rate_limit: float = 1.0
    max_pages_per_domain: int = 100
    user_agent: str = "PersonalIndex/0.1.0"
    timeout: int = 30
    respect_robots_txt: bool = True
    max_content_size: int = 1_000_000  # 1MB

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CrawlerConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Interest:
    """Represents a user-defined interest to track."""

    topic: str
    keywords: list[str] = field(default_factory=list)
    url_patterns: list[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 5  # 1-10, higher = more important

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Interest:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SchedulerConfig:
    """Configuration for scheduled crawling."""

    enabled: bool = False
    interval_hours: int = 24
    max_concurrent_crawls: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SchedulerConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AppConfig:
    """Main application configuration."""

    config_dir: Path = field(default_factory=lambda: DEFAULT_CONFIG_DIR)
    index_dir: Path = field(default_factory=lambda: DEFAULT_INDEX_DIR)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    interests: list[Interest] = field(default_factory=list)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

    def save(self) -> None:
        """Save configuration to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "crawler": self.crawler.to_dict(),
            "interests": [i.to_dict() for i in self.interests],
            "scheduler": self.scheduler.to_dict(),
        }
        with open(self.config_dir / "config.json", "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> AppConfig:
        """Load configuration from disk."""
        path = config_path or DEFAULT_CONFIG_FILE
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        config = cls()
        if "crawler" in data:
            config.crawler = CrawlerConfig.from_dict(data["crawler"])
        if "interests" in data:
            config.interests = [Interest.from_dict(i) for i in data["interests"]]
        if "scheduler" in data:
            config.scheduler = SchedulerConfig.from_dict(data["scheduler"])
        return config
