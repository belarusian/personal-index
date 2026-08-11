"""Data models for personal-index."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum


class InterestType(Enum):
    """Type of interest to track."""
    KEYWORD = "keyword"
    TOPIC = "topic"
    URL_PATTERN = "url_pattern"


class MatchMode(Enum):
    """How keywords should be matched."""
    ANY = "any"
    ALL = "all"
    REGEX = "regex"


@dataclass
class Interest:
    """Represents a user-defined interest to track."""
    name: str
    interest_type: InterestType = InterestType.KEYWORD
    value: str = ""
    keywords: list = field(default_factory=list)
    url_patterns: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    priority: int = 5
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    enabled: bool = True
    topic: str = ""
    match_mode: MatchMode = MatchMode.ANY

    def __post_init__(self):
        """Handle edge case where keywords is passed as int (positional priority)."""
        # Clamp priority to 1-10
        self.priority = max(1, min(10, self.priority))
        if isinstance(self.keywords, int):
            self.priority = self.keywords
            self.keywords = []
        if not isinstance(self.keywords, list):
            self.keywords = []
        if not isinstance(self.url_patterns, list):
            self.url_patterns = []
        if not isinstance(self.topics, list):
            self.topics = []

    def to_dict(self) -> dict:
        """Serialize the interest to a dictionary.

        Returns:
            Dictionary representation of the interest.
        """
        d = asdict(self)
        if isinstance(d.get("interest_type"), InterestType):
            d["interest_type"] = d["interest_type"].value
        if isinstance(d.get("match_mode"), MatchMode):
            d["match_mode"] = d["match_mode"].value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Interest:
        """Create an Interest from a dictionary.

        Args:
            data: Dictionary with interest fields.

        Returns:
            A new Interest instance.
        """
        interest_type = data.get("interest_type", "keyword")
        if isinstance(interest_type, str):
            interest_type = InterestType(interest_type)
        match_mode = data.get("match_mode", "any")
        if isinstance(match_mode, str):
            match_mode = MatchMode(match_mode)
        filtered = {k: v for k, v in data.items()
                    if k in cls.__dataclass_fields__ and k not in ("interest_type", "match_mode")}
        return cls(interest_type=interest_type, match_mode=match_mode, **filtered)

    def matches(self, text: str, url: str = "") -> bool:
        """Check if text/url matches this interest."""
        if not self.enabled:
            return False
        text_lower = text.lower()
        # Check value field as keyword
        if self.value and self.value.lower() in text_lower:
            return True
        # Check keywords list
        for kw in self.keywords:
            if isinstance(kw, str) and kw.lower() in text_lower:
                return True
        for topic in self.topics:
            if topic.lower() in text_lower:
                return True
        for pattern in self.url_patterns:
            try:
                import re
                import fnmatch
                # Try glob-style matching first (*.example.com/*)
                if "*" in pattern and "/" in pattern:
                    if fnmatch.fnmatch(url.lower(), pattern.lower()):
                        return True
                # Then try as regex
                if re.search(pattern, url, re.IGNORECASE):
                    return True
            except (re.error, Exception):
                pass
        return False

    def score(self, text: str) -> float:
        """Calculate relevance score for text."""
        if not self.enabled:
            return 0.0
        text_lower = text.lower()
        total = 0.0
        # Check value field
        if self.value:
            total += text_lower.count(self.value.lower())
        # Check keywords list
        for kw in self.keywords:
            if isinstance(kw, str):
                total += text_lower.count(kw.lower())
        for topic in self.topics:
            total += text_lower.count(topic.lower())
        return min(total * self.priority, self.priority * 10)


@dataclass
class CrawlConfig:
    """Configuration for web crawling behavior."""
    max_depth: int = 3
    politeness_delay: float = 1.0
    rate_limit: int = 10
    max_pages_per_domain: int = 100
    timeout: int = 30
    user_agent: str = "personal-index/0.1.0"
    respect_robots_txt: bool = True
    allowed_domains: list = field(default_factory=list)
    blocked_domains: list = field(default_factory=list)
    max_pages: int = 100
    blocked_extensions: list = field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico",
        ".css", ".js", ".pdf", ".zip", ".tar", ".gz", ".rar",
        ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv",
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".exe", ".bin", ".dmg", ".iso",
    ])
    delay: float = 1.0
    max_concurrent_requests: int = 5
    request_timeout: int = 30

    def to_dict(self) -> dict:
        """Serialize the crawl config to a dictionary.

        Returns:
            Dictionary representation of the config.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CrawlConfig:
        """Create a CrawlConfig from a dictionary.

        Args:
            data: Dictionary with config fields.

        Returns:
            A new CrawlConfig instance.
        """
        return cls(
            **{k: v for k, v in data.items()
               if k in cls.__dataclass_fields__}
        )


@dataclass
class CrawledPage:
    """A page that has been crawled."""
    url: str
    title: str = ""
    content: str = ""
    meta_description: str = ""
    status_code: int = 200
    depth: int = 0
    parent_url: str = ""
    headers: dict = field(default_factory=dict)
    matched_interests: list = field(default_factory=list)
    relevance_score: float = 0.0
    crawled_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Serialize the crawled page to a dictionary.

        Returns:
            Dictionary representation of the page.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CrawledPage:
        """Create a CrawledPage from a dictionary.

        Args:
            data: Dictionary with page fields.

        Returns:
            A new CrawledPage instance.
        """
        crawled_at = data.get("crawled_at", "")
        if isinstance(crawled_at, str) and crawled_at:
            try:
                crawled_at = datetime.fromisoformat(crawled_at)
            except ValueError:
                crawled_at = datetime.now(timezone.utc)
        elif not isinstance(crawled_at, datetime):
            crawled_at = datetime.now(timezone.utc)
        filtered = {k: v for k, v in data.items()
                    if k in cls.__dataclass_fields__ and k != "crawled_at"}
        return cls(**filtered, crawled_at=crawled_at)


@dataclass
class IndexedPage:
    """Represents a crawled and indexed page."""
    url: str
    title: str = ""
    content: str = ""
    keywords: list = field(default_factory=list)
    matched_interests: list = field(default_factory=list)
    crawled_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    domain: str = ""
    status_code: int = 200
    content_length: int = 0
    language: str = "en"
    score: float = 1.0
    indexed_at: str = ""
    source_interest: str = ""
    word_count: int = 0

    def to_dict(self) -> dict:
        """Serialize the indexed page to a dictionary.

        Returns:
            Dictionary representation of the page.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> IndexedPage:
        """Create an IndexedPage from a dictionary.

        Args:
            data: Dictionary with page fields.

        Returns:
            A new IndexedPage instance.
        """
        return cls(
            **{k: v for k, v in data.items()
               if k in cls.__dataclass_fields__}
        )


@dataclass
class SearchResult:
    """Represents a search result."""
    url: str = ""
    title: str = ""
    snippet: str = ""
    relevance_score: float = 0.0
    matched_terms: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize the search result to a dictionary.

        Returns:
            Dictionary representation of the search result.
        """
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score,
            "matched_terms": self.matched_terms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SearchResult:
        """Create a SearchResult from a dictionary."""
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class Page:
    """A page model for the search index."""
    url: str
    title: str = ""
    content: str = ""
    meta_description: str = ""
    matched_interests: list = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    crawled_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    domain: str = ""
    status_code: int = 200
    content_length: int = 0
    language: str = "en"
    keywords: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize the page to a dictionary.

        Returns:
            Dictionary representation of the page.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Page:
        """Create a Page from a dictionary.

        Args:
            data: Dictionary with page fields.

        Returns:
            A new Page instance.
        """
        return cls(
            **{k: v for k, v in data.items()
               if k in cls.__dataclass_fields__}
        )
@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    enabled: bool = False
    interval_hours: int = 24

    def to_dict(self) -> dict:
        """Convert SchedulerConfig to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SchedulerConfig:
        """Create a SchedulerConfig from a dictionary."""
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class IndexConfig:
    """Index configuration."""
    index_path: str = ".personal_index"
    enable_stemming: bool = True


@dataclass
class AppConfig:
    """Application configuration."""
    interests: list[Interest] = field(default_factory=list)
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    config_dir: str | None = None
    index_dir: str | None = None
    data_dir: str = ".personal_index"
    index: IndexConfig = field(default_factory=IndexConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

    def to_dict(self) -> dict:
        """Convert SchedulerConfig to a dictionary."""
        """Serialize the app config to a dictionary.

        Returns:
            Dictionary representation of the config.
        """
        return {
            "interests": [i.to_dict() for i in self.interests],
            "crawl": self.crawl.to_dict(),
            "data_dir": self.data_dir,
            "index": self.index.to_dict() if hasattr(self.index, 'to_dict') else {},
            "scheduler": self.scheduler.to_dict() if hasattr(self.scheduler, 'to_dict') else {},
        }

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        """Create an AppConfig from a dictionary.

        Args:
            data: Dictionary with config fields.

        Returns:
            A new AppConfig instance.
        """
        interests = [Interest.from_dict(d) for d in data.get("interests", [])]
        crawl = CrawlConfig.from_dict(data.get("crawl", {}))
        index_data = data.get("index", {})
        index = IndexConfig(
            index_path=index_data.get("index_path", ".personal_index"),
            enable_stemming=index_data.get("enable_stemming", True),
        )
        scheduler_data = data.get("scheduler", {})
        scheduler = SchedulerConfig(
            enabled=scheduler_data.get("enabled", False),
            interval_hours=scheduler_data.get("interval_hours", 24),
        )
        return cls(
            interests=interests,
            crawl=crawl,
            data_dir=data.get("data_dir", ".personal_index"),
            index=index,
            scheduler=scheduler,
        )

    @property
    def crawler(self) -> CrawlConfig:
        """Alias for crawl property."""
        return self.crawl

    @crawler.setter
    def crawler(self, value: CrawlConfig):
        """Alias for crawl setter."""
        self.crawl = value
