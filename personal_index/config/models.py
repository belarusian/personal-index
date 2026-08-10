"""Configuration data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class MatchMode(Enum):
    """How keywords should be matched."""

    ANY = "any"
    ALL = "all"
    REGEX = "regex"


@dataclass
class Interest:
    """User interest configuration."""

    name: str
    keywords: List[str] = field(default_factory=list)
    url_patterns: List[str] = field(default_factory=list)
    match_mode: MatchMode = MatchMode.ANY
    priority: int = 5
    enabled: bool = True

    def __post_init__(self):
        self.priority = max(1, min(10, self.priority))


@dataclass
class CrawlerConfig:
    """Crawler configuration."""

    max_depth: int = 3
    politeness_delay: float = 1.0
    rate_limit: int = 10
    timeout: int = 30
    respect_robots_txt: bool = True
    max_concurrent_requests: int = 5
    user_agent: str = "PersonalIndex/0.1.0"


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""

    enabled: bool = False
    interval_hours: int = 24


@dataclass
class IndexConfig:
    """Index configuration."""

    index_path: str = ".personal_index"
    enable_stemming: bool = True


@dataclass
class AppConfig:
    """Top-level application configuration."""

    data_dir: str = ".personal_index"
    interests: List[Interest] = field(default_factory=list)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
