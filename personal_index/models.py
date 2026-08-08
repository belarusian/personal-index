"""Data models for personal-index."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class InterestType(Enum):
    """Types of interests to track."""
    TOPIC = "topic"
    KEYWORD = "keyword"
    URL_PATTERN = "url_pattern"


@dataclass
class Interest:
    """Represents a user-defined interest to track."""

    name: str
    interest_type: InterestType
    value: str
    priority: int = 5  # 1-10 scale, default 5
    created_at: datetime = field(default_factory=datetime.utcnow)
    enabled: bool = True

    def matches(self, text: str, url: str = "") -> bool:
        """Check if given text/url matches this interest."""
        if not self.enabled:
            return False

        if self.interest_type == InterestType.KEYWORD:
            return self.value.lower() in text.lower()
        elif self.interest_type == InterestType.TOPIC:
            # Topic matches if any of the space-separated terms appear
            terms = self.value.lower().split()
            text_lower = text.lower()
            return any(term in text_lower for term in terms)
        elif self.interest_type == InterestType.URL_PATTERN:
            try:
                return bool(re.search(self.value, url))
            except re.error:
                return False
        return False

    def score(self, text: str, url: str = "") -> float:
        """Return a relevance score for this interest against text/url."""
        if not self.enabled:
            return 0.0

        if self.interest_type == InterestType.KEYWORD:
            count = text.lower().count(self.value.lower())
            return count * self.priority
        elif self.interest_type == InterestType.TOPIC:
            terms = self.value.lower().split()
            text_lower = text.lower()
            matches = sum(1 for term in terms if term in text_lower)
            return (matches / max(len(terms), 1)) * self.priority
        elif self.interest_type == InterestType.URL_PATTERN:
            try:
                if re.search(self.value, url):
                    return float(self.priority)
            except re.error:
                pass
        return 0.0


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
    matched_interests: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    depth: int = 0
    parent_url: Optional[str] = None
