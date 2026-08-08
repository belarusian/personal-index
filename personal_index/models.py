"""Data models for personal-index."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
import json


@dataclass
class Interest:
    """Represents a user-defined interest to track."""
    name: str
    keywords: list = field(default_factory=list)
    url_patterns: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Interest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CrawlConfig:
    """Configuration for web crawling behavior."""
    max_depth: int = 3
    politeness_delay: float = 1.0  # seconds between requests to same host
    rate_limit: int = 10  # max requests per minute per host
    max_pages_per_domain: int = 100
    timeout: int = 30  # seconds
    user_agent: str = "personal-index/0.1.0"
    respect_robots_txt: bool = True
    allowed_domains: list = field(default_factory=list)
    blocked_domains: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class IndexedPage:
    """Represents a crawled and indexed page."""
    url: str
    title: str = ""
    content: str = ""
    keywords: list = field(default_factory=list)
    matched_interests: list = field(default_factory=list)
    crawled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    domain: str = ""
    status_code: int = 200
    content_length: int = 0
    language: str = "en"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "IndexedPage":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SearchResult:
    """Represents a search result."""
    page: IndexedPage
    score: float = 0.0
    matched_terms: list = field(default_factory=list)
    snippet: str = ""

    def to_dict(self) -> dict:
        return {
            "page": self.page.to_dict(),
            "score": self.score,
            "matched_terms": self.matched_terms,
            "snippet": self.snippet,
        }
