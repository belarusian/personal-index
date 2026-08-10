"""Content filtering engine."""

from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass, field
from typing import List, Set

from personal_index.config.models import Interest


@dataclass
class FilterResult:
    """Result of content filtering."""

    matched: bool = False
    matching_interests: Set[str] = field(default_factory=set)
    matched_keywords: Set[str] = field(default_factory=set)
    score: float = 0.0
    passed: bool = True
    reasons: List[str] = field(default_factory=list)


class ContentFilter:
    """Filters content based on user interests."""

    def __init__(
        self, interests: List[Interest], min_relevance_score: float = 0.0
    ):
        self.interests = interests
        self.min_relevance_score = min_relevance_score
        self._compiled_patterns = self._compile_url_patterns()

    def _compile_url_patterns(self) -> List[tuple]:
        """Compile URL patterns with their interest names."""
        patterns = []
        for interest in self.interests:
            if not interest.enabled:
                continue
            for pattern in interest.url_patterns:
                with suppress(re.error):
                    patterns.append((interest.name, re.compile(pattern)))
        return patterns

    def filter_url(self, url: str) -> FilterResult:
        """Filter a URL against interest patterns."""
        result = FilterResult()
        for name, pattern in self._compiled_patterns:
            if pattern.search(url):
                result.matched = True
                result.matching_interests.add(name)
        return result

    def filter_content(self, content: str, title: str = "") -> FilterResult:
        """Filter content against interest keywords."""
        result = FilterResult()
        text = f"{title} {content}".lower()

        for interest in self.interests:
            if not interest.enabled:
                continue
            for kw in interest.keywords:
                kw_lower = kw.lower()
                if kw_lower in text:
                    result.matched = True
                    result.matching_interests.add(interest.name)
                    result.matched_keywords.add(kw)
                    result.score += interest.priority

        return result

    def filter_page(self, page_or_url, content: str = "", title: str = "") -> FilterResult:
        """Filter a page (Page object or URL string) against interests."""
        # Handle Page object
        if hasattr(page_or_url, 'url'):
            url = page_or_url.url
            if not content:
                content = getattr(page_or_url, 'content', '')
            if not title:
                title = getattr(page_or_url, 'title', '')
        else:
            url = page_or_url

        url_result = self.filter_url(url)
        content_result = self.filter_content(content, title)

        result = FilterResult(
            matched=url_result.matched or content_result.matched,
            matching_interests=(
                url_result.matching_interests
                | content_result.matching_interests
            ),
            matched_keywords=content_result.matched_keywords,
            score=url_result.score + content_result.score,
            passed=url_result.matched or content_result.matched,
        )
        return result

    def update_page(self, page, result: FilterResult) -> None:
        """Update a page object with filter results."""
        if hasattr(page, 'matched_interests'):
            page.matched_interests = list(result.matching_interests)
        if hasattr(page, 'relevance_score'):
            page.relevance_score = result.score

    def should_crawl(self, url: str) -> bool:
        """Check if URL should be crawled based on patterns."""
        if not self._compiled_patterns:
            return True
        for _, pattern in self._compiled_patterns:
            if pattern.search(url):
                return True
        return False

    def extract_relevant_text(self, text: str, max_length: int = 500) -> str:
        """Extract relevant text, truncating if needed."""
        if len(text) <= max_length:
            return text
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.5:
            truncated = truncated[:last_space]
        return truncated.rstrip()
