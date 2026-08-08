"""Core data models for Personal Index."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PageStatus(Enum):
    """Status of a crawled page."""

    PENDING = "pending"
    CRAWLED = "crawled"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class URL:
    """Represents a URL to crawl or that has been crawled."""

    url: str
    depth: int = 0
    status: PageStatus = PageStatus.PENDING
    domain: str = ""
    parent_url: Optional[str] = None
    crawled_at: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.domain:
            self.domain = self._extract_domain()

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        url = url.split("://", 1)[-1] if "://" in url else url
        return url.split("/")[0].split(":")[0].split("@")[-1]

    @property
    def id(self) -> str:
        """Generate unique ID for this URL."""
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "depth": self.depth,
            "status": self.status.value,
            "domain": self.domain,
            "parent_url": self.parent_url,
            "crawled_at": self.crawled_at.isoformat() if self.crawled_at else None,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> URL:
        crawled_at = None
        if data.get("crawled_at"):
            crawled_at = datetime.fromisoformat(data["crawled_at"])
        return cls(
            url=data["url"],
            depth=data.get("depth", 0),
            status=PageStatus(data.get("status", "pending")),
            domain=data.get("domain", ""),
            parent_url=data.get("parent_url"),
            crawled_at=crawled_at,
            error=data.get("error"),
        )


@dataclass
class Page:
    """Represents a crawled page with its content."""

    url: str
    title: str = ""
    content: str = ""
    meta_description: str = ""
    links: list[str] = field(default_factory=list)
    crawled_at: Optional[datetime] = None
    status_code: int = 200
    content_type: str = "text/html"
    content_length: int = 0
    matched_interests: list[str] = field(default_factory=list)
    relevance_score: float = 0.0

    @property
    def id(self) -> str:
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "meta_description": self.meta_description,
            "links": self.links,
            "crawled_at": self.crawled_at.isoformat() if self.crawled_at else None,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "content_length": self.content_length,
            "matched_interests": self.matched_interests,
            "relevance_score": self.relevance_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Page:
        crawled_at = None
        if data.get("crawled_at"):
            crawled_at = datetime.fromisoformat(data["crawled_at"])
        return cls(
            url=data["url"],
            title=data.get("title", ""),
            content=data.get("content", ""),
            meta_description=data.get("meta_description", ""),
            links=data.get("links", []),
            crawled_at=crawled_at,
            status_code=data.get("status_code", 200),
            content_type=data.get("content_type", "text/html"),
            content_length=data.get("content_length", 0),
            matched_interests=data.get("matched_interests", []),
            relevance_score=data.get("relevance_score", 0.0),
        )
