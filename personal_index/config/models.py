"""Configuration models for personal-index."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class MatchMode(Enum):
    """How interest matching should work."""
    ANY = "any"       # Match if any keyword matches
    ALL = "all"       # Match if all keywords match
    REGEX = "regex"   # Match using regex patterns


@dataclass
class Interest:
    """Represents a user-defined interest to track."""

    name: str
    keywords: list[str] = field(default_factory=list)
    url_patterns: list[str] = field(default_factory=list)
    match_mode: MatchMode = MatchMode.ANY
    priority: int = 5  # 1-10, higher = more important
    enabled: bool = True

    def __post_init__(self):
        if self.priority < 1:
            self.priority = 1
        if self.priority > 10:
            self.priority = 10


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler."""

    max_depth: int = 3
    max_pages_per_domain: int = 100
    politeness_delay: float = 1.0  # seconds between requests to same domain
    rate_limit: int = 10  # max requests per minute
    timeout: int = 30  # request timeout in seconds
    user_agent: str = "personal-index/0.1.0"
    respect_robots_txt: bool = True
    max_content_size: int = 1_000_000  # 1MB max page size
    allowed_extensions: list[str] = field(
        default_factory=lambda: [".html", ".htm", ".xml", ".json"]
    )


@dataclass
class SchedulerConfig:
    """Configuration for scheduled crawling."""

    enabled: bool = False
    interval_hours: int = 24
    max_concurrent_crawls: int = 1
    crawl_all_interests: bool = True


@dataclass
class IndexConfig:
    """Configuration for the search index."""

    index_path: str = ".personal_index"
    min_term_freq: int = 1
    max_index_size_mb: int = 500
    enable_stemming: bool = True
    enable_stop_words: bool = True


@dataclass
class AppConfig:
    """Top-level application configuration."""

    data_dir: str = ".personal_index"
    interests: list[Interest] = field(default_factory=list)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
