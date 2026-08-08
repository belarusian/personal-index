"""Content filtering module for filtering pages based on interests."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from personal_index.interest_store import InterestStore
from personal_index.models import CrawledPage, Interest


@dataclass
class FilterConfig:
    """Configuration for content filtering."""

    min_content_length: int = 100
    max_content_length: int = 100000
    min_title_length: int = 3
    require_interest_match: bool = True
    blocked_domains: list[str] = field(default_factory=list)
    blocked_patterns: list[str] = field(default_factory=list)
    required_patterns: list[str] = field(default_factory=list)
    min_relevance_score: float = 0.0


class ContentFilter:
    """Filter crawled content based on interests and rules."""

    def __init__(
        self,
        config: Optional[FilterConfig] = None,
        interest_store: Optional[InterestStore] = None,
    ):
        self.config = config or FilterConfig()
        self.interest_store = interest_store
        self._blocked_regexes = []
        self._required_regexes = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile blocked and required regex patterns."""
        for pattern in self.config.blocked_patterns:
            try:
                self._blocked_regexes.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                pass
        for pattern in self.config.required_patterns:
            try:
                self._required_regexes.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                pass

    def should_include(self, page: CrawledPage) -> bool:
        """Determine if a page should be included in the index."""
        if not self._check_domain(page.url):
            return False

        if not self._check_content_length(page):
            return False

        if not self._check_title_length(page):
            return False

        if not self._check_blocked_patterns(page):
            return False

        if not self._check_required_patterns(page):
            return False

        if self.config.require_interest_match and self.interest_store:
            if not self._check_interest_match(page):
                return False

        if page.relevance_score < self.config.min_relevance_score:
            return False

        return True

    def _check_domain(self, url: str) -> bool:
        """Check if URL domain is not blocked."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        for blocked in self.config.blocked_domains:
            if domain.endswith(blocked.lower()):
                return False
        return True

    def _check_content_length(self, page: CrawledPage) -> bool:
        """Check if content meets length requirements."""
        content_len = len(page.content)
        return (
            self.config.min_content_length <= content_len <= self.config.max_content_length
        )

    def _check_title_length(self, page: CrawledPage) -> bool:
        """Check if title meets minimum length."""
        return len(page.title) >= self.config.min_title_length

    def _check_blocked_patterns(self, page: CrawledPage) -> bool:
        """Check that content doesn't match blocked patterns."""
        text = f"{page.title} {page.content}"
        for regex in self._blocked_regexes:
            if regex.search(text):
                return False
        return True

    def _check_required_patterns(self, page: CrawledPage) -> bool:
        """Check that content matches at least one required pattern."""
        if not self._required_regexes:
            return True
        text = f"{page.title} {page.content}"
        return any(regex.search(text) for regex in self._required_regexes)

    def _check_interest_match(self, page: CrawledPage) -> bool:
        """Check if page matches any interests."""
        text = f"{page.title} {page.content} {page.meta_description}"
        matching = self.interest_store.matches_any(text, page.url)
        if matching:
            page.matched_interests = [m.name for m in matching]
            page.relevance_score = self.interest_store.total_score(text, page.url)
        return len(matching) > 0

    def filter_pages(self, pages: list[CrawledPage]) -> list[CrawledPage]:
        """Filter a list of pages, returning only those that pass."""
        return [page for page in pages if self.should_include(page)]

    def get_filter_reasons(self, page: CrawledPage) -> list[str]:
        """Return list of reasons why a page was filtered out."""
        reasons = []
        if not self._check_domain(page.url):
            reasons.append("blocked domain")
        if not self._check_content_length(page):
            reasons.append(f"content length {len(page.content)} out of range")
        if not self._check_title_length(page):
            reasons.append(f"title too short ({len(page.title)} chars)")
        if not self._check_blocked_patterns(page):
            reasons.append("matches blocked pattern")
        if not self._check_required_patterns(page):
            reasons.append("doesn't match required pattern")
        if self.config.require_interest_match and self.interest_store:
            if not self._check_interest_match(page):
                reasons.append("no interest match")
        if page.relevance_score < self.config.min_relevance_score:
            reasons.append(f"relevance score {page.relevance_score} below minimum")
        return reasons
