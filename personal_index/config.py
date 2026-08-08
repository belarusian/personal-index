"""Configuration management for personal-index."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "personal-index"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler."""

    max_depth: int = 3
    politeness_delay: float = 1.0
    rate_limit: float = 1.0
    max_pages_per_domain: int = 100
    timeout: int = 30
    user_agent: str = "personal-index/0.1.0"
    respect_robots_txt: bool = True
    allowed_extensions: List[str] = field(
        default_factory=lambda: [".html", ".htm", ".xml"]
    )
    max_content_length: int = 1_000_000

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlerConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Interest:
    """Represents a user-defined interest to track."""

    topic: str
    keywords: List[str] = field(default_factory=list)
    url_patterns: List[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 5

    def matches(self, text: str) -> bool:
        """Check if given text matches this interest."""
        if not self.enabled:
            return False
        text_lower = text.lower()
        if self.keywords:
            return any(kw.lower() in text_lower for kw in self.keywords)
        return self.topic.lower() in text_lower

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Interest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ScheduleConfig:
    """Configuration for scheduled crawling."""

    enabled: bool = False
    interval_hours: int = 24
    last_run: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AppConfig:
    """Main application configuration."""

    config_dir: Path = field(default_factory=lambda: DEFAULT_CONFIG_DIR)
    data_dir: Path = field(default_factory=lambda: DEFAULT_CONFIG_DIR / "data")
    index_dir: Path = field(default_factory=lambda: DEFAULT_CONFIG_DIR / "index")
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    interests: List[Interest] = field(default_factory=list)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)

    def ensure_dirs(self) -> None:
        """Create necessary directories."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        return {
            "crawler": self.crawler.to_dict(),
            "interests": [i.to_dict() for i in self.interests],
            "schedule": self.schedule.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        crawler = CrawlerConfig.from_dict(data.get("crawler", {}))
        interests = [Interest.from_dict(i) for i in data.get("interests", [])]
        schedule = ScheduleConfig.from_dict(data.get("schedule", {}))
        return cls(crawler=crawler, interests=interests, schedule=schedule)

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        self.ensure_dirs()
        filepath = path or DEFAULT_CONFIG_FILE
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        """Load configuration from file."""
        filepath = path or DEFAULT_CONFIG_FILE
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
            return cls.from_dict(data)
        return cls()
