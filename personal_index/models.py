"""Data models for personal-index."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class InterestType(Enum):
    """Types of interests that can be tracked."""
    TOPIC = "topic"
    KEYWORD = "keyword"
    URL_PATTERN = "url_pattern"


@dataclass
class Interest:
    """Represents a user-defined interest to track."""

    topic: str
    keywords: list[str] = field(default_factory=list)
    url_patterns: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    enabled: bool = True

    @property
    def id(self) -> str:
        """Generate a unique ID from the topic."""
        return hashlib.sha256(self.topic.encode()).hexdigest()[:16]

    def matches_text(self, text: str) -> bool:
        """Check if text matches any of the interest keywords."""
        if not self.keywords:
            return False
        text_lower = text.lower()
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                return True
        return False

    def matches_url(self, url: str) -> bool:
        """Check if URL matches any of the interest URL patterns."""
        url_lower = url.lower()
        for pattern in self.url_patterns:
            if pattern.lower() in url_lower:
                return True
        return False


@dataclass
class CrawledPage:
    """Represents a crawled web page."""

    url: str
    title: str = ""
    content: str = ""
    meta_description: str = ""
    headers: dict = field(default_factory=dict)
    status_code: int = 0
    crawled_at: datetime = field(default_factory=datetime.utcnow)
    depth: int = 0
    parent_url: Optional[str] = None
    matched_interests: list[str] = field(default_factory=list)
    word_count: int = 0

    @property
    def id(self) -> str:
        """Generate a unique ID from the URL."""
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]

    @property
    def searchable_text(self) -> str:
        """Get text suitable for indexing."""
        parts = [self.title, self.meta_description, self.content]
        return " ".join(p for p in parts if p)


@dataclass
class SearchResult:
    """Represents a search result."""

    page: CrawledPage
    score: float = 0.0
    highlights: list[str] = field(default_factory=list)
    matched_interest: Optional[str] = None


@dataclass
class CrawlConfig:
    """Configuration for the web crawler."""

    max_depth: int = 2
    max_pages: int = 100
    rate_limit: float = 1.0  # seconds between requests
    politeness_delay: float = 0.5  # minimum delay between requests to same host
    timeout: int = 10  # request timeout in seconds
    user_agent: str = "personal-index/0.1.0"
    respect_robots: bool = True
    allowed_domains: list[str] = field(default_factory=list)
    blocked_domains: list[str] = field(default_factory=list)
    max_content_length: int = 1_000_000  # 1MB max page content


@dataclass
class CrawlStats:
    """Statistics about a crawl run."""

    pages_crawled: int = 0
    pages_filtered: int = 0
    pages_stored: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    urls_queued: int = 0

    @property
    def duration(self) -> Optional[float]:
        """Duration of crawl in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
