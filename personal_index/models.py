"""Core data models for Personal Index."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class InterestType(Enum):
    """Type of interest matching."""

    KEYWORD = "keyword"
    TOPIC = "topic"
    URL_PATTERN = "url_pattern"


@dataclass
class Interest:
    """Represents a user interest for content matching."""

    name: str
    interest_type: InterestType = InterestType.KEYWORD
    value: str = ""
    priority: int = 5
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self.priority = max(1, min(10, self.priority))

    def matches(self, text: str, url: str = "") -> bool:
        """Check if this interest matches the given text/url."""
        if not self.enabled:
            return False

        if self.interest_type == InterestType.KEYWORD:
            return self._match_keyword(text)
        elif self.interest_type == InterestType.TOPIC:
            return self._match_topic(text)
        elif self.interest_type == InterestType.URL_PATTERN:
            return self._match_url_pattern(url)
        return False

    def _match_keyword(self, text: str) -> bool:
        """Match keyword in text (case-insensitive)."""
        if not text or not self.value:
            return False
        return self.value.lower() in text.lower()

    def _match_topic(self, text: str) -> bool:
        """Match any topic term in text (case-insensitive)."""
        if not text or not self.value:
            return False
        terms = self.value.lower().split()
        text_lower = text.lower()
        return any(term in text_lower for term in terms)

    def _match_url_pattern(self, url: str) -> bool:
        """Match URL against regex pattern."""
        if not url or not self.value:
            return False
        try:
            return bool(re.search(self.value, url))
        except re.error:
            return False

    def score(self, text: str) -> float:
        """Calculate relevance score for this interest against text."""
        if not self.enabled or not text:
            return 0.0

        if self.interest_type == InterestType.KEYWORD:
            return self._keyword_score(text)
        elif self.interest_type == InterestType.TOPIC:
            return self._topic_score(text)
        return 0.0

    def _keyword_score(self, text: str) -> float:
        """Score based on keyword occurrence count * priority."""
        if not self.value:
            return 0.0
        count = text.lower().count(self.value.lower())
        return count * self.priority

    def _topic_score(self, text: str) -> float:
        """Score based on fraction of topic terms matched * priority."""
        if not self.value:
            return 0.0
        terms = self.value.lower().split()
        if not terms:
            return 0.0
        text_lower = text.lower()
        matched = sum(1 for term in terms if term in text_lower)
        return (matched / len(terms)) * self.priority


@dataclass
class CrawledPage:
    """Represents a crawled web page."""

    url: str
    title: str = ""
    content: str = ""
    meta_description: str = ""
    status_code: int = 0
    depth: int = 0
    parent_url: Optional[str] = None
    headers: dict = field(default_factory=dict)
    matched_interests: list = field(default_factory=list)
    relevance_score: float = 0.0
    crawled_at: datetime = field(default_factory=datetime.utcnow)
