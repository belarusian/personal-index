"""Content filtering based on user interests."""

from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass, field

from personal_index.interests import InterestStore
from personal_index.models import CrawledPage


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
    """Filters crawled pages based on interests and configuration."""

    def __init__(
        self,
        config: FilterConfig | None = None,
        interest_store: InterestStore | None = None,
    ):
        self.config = config or FilterConfig()
        self.interest_store = interest_store
        self._compiled_blocked = self._compile_patterns(self.config.blocked_patterns)
        self._compiled_required = self._compile_patterns(self.config.required_patterns)

    @staticmethod
    def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
        """Compile regex patterns, ignoring invalid ones."""
        compiled = []
        for pattern in patterns:
            with suppress(re.error):
                compiled.append(re.compile(pattern, re.IGNORECASE))
        return compiled

    def should_include(self, page: CrawledPage) -> bool:
        """Determine if a page should be included in the index."""
        reasons = self.get_filter_reasons(page)
        return len(reasons) == 0

    def get_filter_reasons(self, page: CrawledPage) -> list[str]:
        """Get list of reasons why a page was filtered out."""
        reasons = []

        # Check content length
        if len(page.content) < self.config.min_content_length:
            reasons.append(f"content length ({len(page.content)}) below minimum ({self.config.min_content_length})")

        if len(page.content) > self.config.max_content_length:
            reasons.append(f"content length ({len(page.content)}) exceeds maximum ({self.config.max_content_length})")

        # Check title length
        if len(page.title) < self.config.min_title_length:
            reasons.append(f"title too short ({len(page.title)} < {self.config.min_title_length})")

        # Check blocked domains
        if self._is_blocked_domain(page.url):
            reasons.append("domain is blocked")

        # Check blocked patterns
        if self._matches_blocked_patterns(page):
            reasons.append("content matches blocked pattern")

        # Check required patterns
        if self._compiled_required and not self._matches_required_patterns(page):
            reasons.append("content does not match required pattern")

        # Check interest match
        if self.config.require_interest_match and self.interest_store and not self._matches_interests(page):
            reasons.append("no matching interests")

        # Check minimum relevance score
        if self.interest_store and self.config.min_relevance_score > 0:
            score = self.interest_store.total_score(page.content)
            if score < self.config.min_relevance_score:
                reasons.append(f"relevance score ({score}) below minimum ({self.config.min_relevance_score})")

        return reasons

    def _is_blocked_domain(self, url: str) -> bool:
        """Check if URL domain is blocked."""
        from personal_index.url_utils import extract_domain

        domain = extract_domain(url)
        for blocked in self.config.blocked_domains:
            if domain == blocked or domain.endswith("." + blocked):
                return True
        return False

    def _matches_blocked_patterns(self, page: CrawledPage) -> bool:
        """Check if page content matches any blocked patterns."""
        text = f"{page.title} {page.content}"
        return any(pattern.search(text) for pattern in self._compiled_blocked)

    def _matches_required_patterns(self, page: CrawledPage) -> bool:
        """Check if page content matches any required patterns."""
        text = f"{page.title} {page.content}"
        return any(pattern.search(text) for pattern in self._compiled_required)

    def _matches_interests(self, page: CrawledPage) -> bool:
        """Check if page matches any interests."""
        if not self.interest_store:
            return True
        text = f"{page.title} {page.content}"
        matches = self.interest_store.matches_any(text, page.url)
        if matches:
            page.matched_interests = [m.name for m in matches]
            page.relevance_score = self.interest_store.total_score(text)
            return True
        return False

    def filter_pages(self, pages: list[CrawledPage]) -> list[CrawledPage]:
        """Filter a list of pages, returning only included ones."""
        return [page for page in pages if self.should_include(page)]
